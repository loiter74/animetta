import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import { BotRuntimeClient } from '../src/mcp/runtimeClient.js';

function fixture(kill) {
  const child = new EventEmitter();
  Object.assign(child, { exitCode: null, signalCode: null, kill });
  const runtime = new BotRuntimeClient({ entrypoint: '', cwd: '', eventBuffer: {} });
  runtime.process = child;
  return { runtime, child };
}

test('runtime stop retains ownership until the forced child actually exits', async () => {
  const signals = [];
  const { runtime, child } = fixture((signal) => {
    signals.push(signal || 'SIGTERM');
    if (signal === 'SIGKILL') setTimeout(() => {
      child.signalCode = 'SIGKILL';
      child.emit('exit', null, 'SIGKILL');
    }, 2);
  });
  await runtime.stop({ timeoutMs: 5 });
  assert.deepEqual(signals, ['SIGTERM', 'SIGKILL']);
  assert.equal(child.signalCode, 'SIGKILL');
  assert.equal(runtime.process, null);
  assert.equal(child.listenerCount('exit'), 0);
});

test('unconfirmed termination fails and preserves the process handle', async () => {
  const { runtime, child } = fixture(() => {});
  await assert.rejects(runtime.stop({ timeoutMs: 2 }), /RUNTIME_STOP_TIMEOUT/);
  assert.equal(runtime.process, child);
  assert.equal(child.listenerCount('exit'), 0);
});

test('signal exit already observed needs no second kill', async () => {
  const { runtime, child } = fixture(() => { throw new Error('already exited'); });
  child.signalCode = 'SIGTERM';
  await runtime.stop({ timeoutMs: 2 });
  assert.equal(runtime.process, null);
});
