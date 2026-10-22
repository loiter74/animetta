import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';

export class BotRuntimeClient {
  constructor({ entrypoint, cwd, eventBuffer, spawnProcess = spawn }) {
    this.entrypoint = entrypoint;
    this.cwd = cwd;
    this.eventBuffer = eventBuffer;
    this.spawnProcess = spawnProcess;
    this.process = null;
    this.pending = new Map();
    this.nextId = 1;
    this.waiters = new Set();
  }

  get running() {
    return Boolean(this.process && this.process.exitCode === null);
  }

  async start({
    host,
    port,
    username,
    version,
    viewer = {},
    presentation = {},
    timeoutMs = 20_000,
  }) {
    if (this.running) return;
    const args = [this.entrypoint, host, String(port), username];
    if (version) args.push(version);
    const env = {
      ...process.env,
      GAMEBOT_CONTROL_PLANE_MODE: 'true',
      GAMEBOT_PRESENTATION_MODE: presentation.mode ?? 'off',
      GAMEBOT_PRESENTATION_TEMPO: presentation.tempo ?? 'normal',
      GAMEBOT_PRESENTATION_SEED: presentation.seed ?? 'animetta-live-v1',
      MC_CLIENT_VIEWER_ENABLED: viewer.username ? 'true' : 'false',
      MC_CLIENT_VIEWER_USERNAME: viewer.username || '',
      MC_CLIENT_VIEWER_MODE: 'spectator',
      MC_CLIENT_VIEWER_AUTO_SPECTATE: viewer.auto_attach === false ? 'false' : 'true',
      MC_CLIENT_VIEWER_POLL_INTERVAL: String(viewer.poll_interval_seconds ?? 20),
      MC_CLIENT_VIEWER_SPECTATE_TIMEOUT: String(viewer.spectate_timeout_seconds ?? 8),
    };
    this.process = this.spawnProcess(process.execPath, args, {
      cwd: this.cwd,
      env,
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    });
    this.#consumeStdout();
    this.process.stderr?.on('data', (chunk) => {
      const message = String(chunk).trim();
      if (message) this.eventBuffer.append({ type: 'runtime_log', level: 'warning', message });
    });
    this.process.once('exit', (code, signal) => {
      this.eventBuffer.append({ type: 'runtime_exit', code, signal });
      for (const pending of this.pending.values()) pending.resolve(this.#error('RUNTIME_EXITED'));
      this.pending.clear();
      this.#notifyWaiters({ type: 'runtime_exit', code, signal });
    });
    await this.waitForEvent((event) => event.type === 'login', timeoutMs);
  }

  async stop({ timeoutMs = 5_000 } = {}) {
    const child = this.process;
    if (!child) return;
    const hasExited = () => child.exitCode != null || child.signalCode != null;
    const waitForExit = () => new Promise((resolve) => {
      if (hasExited()) { resolve(true); return; }
      let timer;
      const finish = (exited) => {
        clearTimeout(timer);
        child.removeListener('exit', onExit);
        resolve(exited);
      };
      const onExit = () => finish(true);
      child.once('exit', onExit);
      timer = setTimeout(() => finish(false), timeoutMs);
    });
    if (!hasExited()) {
      const gracefulExit = waitForExit();
      child.kill();
      if (!await gracefulExit) {
        const forcedExit = waitForExit();
        child.kill('SIGKILL');
        if (!await forcedExit) throw new Error('RUNTIME_STOP_TIMEOUT');
      }
    }
    if (this.process === child) this.process = null;
  }

  async send(action, params = {}, timeoutMs = 60_000) {
    if (!this.running || !this.process?.stdin) return this.#error('RUNTIME_NOT_READY');
    const id = this.nextId++;
    let timer;
    const response = new Promise((resolve) => {
      timer = setTimeout(() => {
        this.pending.delete(id);
        resolve(this.#error('RUNTIME_TIMEOUT'));
      }, timeoutMs);
      this.pending.set(id, { resolve });
    });
    this.process.stdin.write(`${JSON.stringify({ id, action, params, timeout_ms: timeoutMs })}\n`);
    const result = await response;
    clearTimeout(timer);
    return result;
  }

  waitForEvent(predicate, timeoutMs) {
    return new Promise((resolve, reject) => {
      const waiter = { predicate, resolve, reject };
      const timer = setTimeout(() => {
        this.waiters.delete(waiter);
        reject(new Error('RUNTIME_EVENT_TIMEOUT'));
      }, timeoutMs);
      waiter.resolve = (event) => {
        clearTimeout(timer);
        resolve(event);
      };
      this.waiters.add(waiter);
    });
  }

  #consumeStdout() {
    if (!this.process?.stdout) return;
    const lines = createInterface({ input: this.process.stdout, terminal: false });
    lines.on('line', (line) => {
      let message;
      try {
        message = JSON.parse(line);
      } catch {
        this.eventBuffer.append({ type: 'runtime_log', level: 'warning', message: line.slice(0, 500) });
        return;
      }
      if (message.status === 'event' && (message.id === null || message.id === 'system')) {
        const event = message.result ?? {};
        this.eventBuffer.append(event);
        this.#notifyWaiters(event);
        return;
      }
      const pending = this.pending.get(message.id);
      if (pending) {
        this.pending.delete(message.id);
        pending.resolve({ status: message.status, result: message.result });
      }
    });
  }

  #notifyWaiters(event) {
    for (const waiter of [...this.waiters]) {
      if (!waiter.predicate(event)) continue;
      this.waiters.delete(waiter);
      waiter.resolve(event);
    }
  }

  #error(code) {
    return { status: 'error', result: { code, message: code } };
  }
}
