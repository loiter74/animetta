// Runtime measurement only: never called by the ordinary build/test commands.
import { chromium } from 'playwright'
import { createHash, randomUUID } from 'node:crypto'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import { parseArgs } from 'node:util'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const { values } = parseArgs({
  options: {
    url: { type: 'string', default: 'http://localhost:3000' },
    mode: { type: 'string', default: 'surfaces' },
    phase: { type: 'string', default: 'after' },
    output: { type: 'string' },
    samples: { type: 'string', default: '5' },
    root: { type: 'string' },
  },
})
const root = path.resolve(values.root ?? fileURLToPath(new URL('../..', import.meta.url)))
const output = path.resolve(values.output ?? 'artifacts/startup-performance/browser.json')
const samplesRequested = values.mode === 'surfaces' ? 1 : Number(values.samples)
if (!['surfaces', 'frontend', 'backend'].includes(values.mode)) throw new Error('Unknown mode')
if (!Number.isInteger(samplesRequested) || samplesRequested < 1) throw new Error('Invalid samples')
const token = process.env.ANIMETTA_ACCESS_TOKEN
if (!token) throw new Error('ANIMETTA_ACCESS_TOKEN is required')
const base = new URL(values.url)
if (!['localhost', '127.0.0.1'].includes(base.hostname)) throw new Error('Loopback URL required')
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex')
const compose = (...args) =>
  execFileSync('docker', ['compose', ...args], { cwd: root, encoding: 'utf8', timeout: 30000 })
const runtime = () => {
  const id = compose('ps', '--all', '--quiet', 'animetta').trim()
  if (!id) throw new Error('Application container missing')
  const [item] = JSON.parse(
    execFileSync('docker', ['inspect', id], { encoding: 'utf8', timeout: 10000 }),
  )
  return { id: item.Id, image: item.Image, startedAt: item.State.StartedAt }
}
const waitUntil = async (check, timeout = 120000) => {
  const deadline = performance.now() + timeout
  let lastError
  while (performance.now() < deadline) {
    try {
      if (await check()) return
    } catch (error) {
      lastError = error
    }
    await new Promise((resolve) => setTimeout(resolve, 100))
  }
  throw new Error(`Readiness timed out: ${lastError?.message ?? 'condition not met'}`)
}
const ready = async () => {
  const response = await fetch(new URL('/ready', base), {
    headers: { Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(3000),
  })
  if (response.status === 401 || response.status === 403)
    throw new Error('Readiness authentication failed')
  if (!response.ok) return false
  const body = await response.json()
  if ('ready' in body) return body.ready === true
  return body.ready === true || ['ok', 'ready'].includes(body.status)
}
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  extraHTTPHeaders: { Authorization: `Bearer ${token}` },
})
// The existing machine-token contract authenticates HTTP and Socket.IO.
// Keep those credentials on the measured origin, including redirected requests.
await context.route('**/*', (route) =>
  new URL(route.request().url()).origin === base.origin
    ? route.continue()
    : route.abort('blockedbyclient'),
)
const dashboard = await context.newPage()
const live = await context.newPage()
let checkingSurfaces = true
const surfaceErrors = []
const safeError = (value) => String(value).replaceAll(token, '[redacted]')
for (const page of [dashboard, live]) {
  page.on('pageerror', (error) => {
    if (checkingSurfaces) surfaceErrors.push({ kind: 'pageerror', error: safeError(error.message) })
  })
  page.on('console', (message) => {
    if (checkingSurfaces && message.type() === 'error')
      surfaceErrors.push({ kind: 'console', error: safeError(message.text()) })
  })
  page.on('requestfailed', (request) => {
    if (checkingSurfaces)
      surfaceErrors.push({ kind: 'requestfailed', path: new URL(request.url()).pathname })
  })
  page.on('response', (response) => {
    if (checkingSurfaces && response.status() >= 400)
      surfaceErrors.push({
        kind: 'http',
        path: new URL(response.url()).pathname,
        status: response.status(),
      })
  })
}
const payload = {
  schema_version: 1,
  scenario: values.mode,
  phase: values.phase,
  samples: [],
  samples_requested: samplesRequested,
  started_at: new Date().toISOString(),
  root,
  url: base.href,
  authentication: 'existing_machine_token',
  surface_errors: surfaceErrors,
}
let source
let original
let changed
try {
  const started = performance.now()
  await waitUntil(ready)
  const session = await context.request.get(new URL('/api/auth/session', base).href)
  if (!session.ok() || !(await session.json()).authenticated)
    throw new Error('Browser session authentication failed')
  await dashboard.goto(new URL('/dashboard', base).href, { waitUntil: 'domcontentloaded' })
  await dashboard.getByTestId('dashboard-page').waitFor({ state: 'visible' })
  await live.goto(new URL('/live.html', base).href, { waitUntil: 'domcontentloaded' })
  await live.locator('#socketStatus[data-state="connected"]').waitFor({ timeout: 120000 })
  await live.locator('#modelStatus[data-state="live"]').waitFor({ timeout: 120000 })
  const resources = []
  for (const page of [dashboard, live]) {
    for (const url of await page
      .locator('script[src]')
      .evaluateAll((nodes) => nodes.map((node) => node.src))) {
      if (new URL(url).origin !== base.origin)
        throw new Error('Cross-origin script is not permitted')
      const response = await context.request.get(url, { maxRedirects: 0 })
      if (!response.ok()) throw new Error(`Resource unavailable: ${url}`)
      resources.push({ url, sha256: sha(await response.body()) })
    }
  }
  payload.surface_seconds = (performance.now() - started) / 1000
  payload.resources = resources
  payload.socket_connected = true
  if (surfaceErrors.length) throw new Error('Browser surface errors; see surface_errors')
  checkingSurfaces = false
  if (values.mode !== 'surfaces') {
    source = path.join(
      root,
      values.mode === 'frontend' ? 'frontend/src/App.vue' : 'src/animetta/core/socketio_server.py',
    )
    original = await readFile(source)
    payload.source = source
    payload.original_sha256 = sha(original)
    for (let index = 1; index <= samplesRequested; index += 1) {
      const before = runtime()
      const timeOrigin = await dashboard.evaluate(() => performance.timeOrigin)
      const marker = `probe-${randomUUID()}`
      const suffix =
        values.mode === 'frontend'
          ? `\n<style> :root { --anima-perf-probe: ${marker}; } </style>\n`
          : `\n# startup-performance ${marker}\n`
      changed = Buffer.concat([original, Buffer.from(suffix)])
      const sampleStarted = performance.now()
      await writeFile(source, changed)
      if (values.mode === 'frontend') {
        await dashboard.waitForFunction(
          (expected) =>
            globalThis
              .getComputedStyle(globalThis.document.documentElement)
              .getPropertyValue('--anima-perf-probe')
              .trim() === expected,
          marker,
          { timeout: 60000, polling: 50 },
        )
        if ((await dashboard.evaluate(() => performance.timeOrigin)) !== timeOrigin)
          throw new Error('Page reloaded instead of HMR')
      } else {
        await waitUntil(() => runtime().startedAt !== before.startedAt)
        await waitUntil(ready)
        const deployed = compose(
          'exec',
          '-T',
          'animetta',
          'python',
          '-c',
          'import hashlib; print(hashlib.sha256(open("/app/src/animetta/core/socketio_server.py", "rb").read()).hexdigest())',
        ).trim()
        if (deployed !== sha(changed)) throw new Error('Backend source fingerprint mismatch')
        await live.locator('#socketStatus[data-state="connected"]').waitFor({ timeout: 120000 })
      }
      const elapsed = (performance.now() - sampleStarted) / 1000
      const after = runtime()
      if (after.image !== before.image) throw new Error('Ordinary source edit rebuilt the image')
      payload.samples.push({
        sample: index,
        wall_seconds: elapsed,
        exit_code: 0,
        before,
        after,
        source_sha256: sha(changed),
      })
      if (!(await readFile(source)).equals(changed))
        throw new Error('Source changed concurrently; refusing to overwrite it')
      await writeFile(source, original)
      changed = null
      if (values.mode === 'frontend') {
        await dashboard.waitForFunction(
          () =>
            !globalThis
              .getComputedStyle(globalThis.document.documentElement)
              .getPropertyValue('--anima-perf-probe')
              .trim(),
        )
      } else {
        await waitUntil(() => runtime().startedAt !== after.startedAt)
        await waitUntil(ready)
      }
    }
  }
  payload.exit_code = 0
} catch (error) {
  payload.exit_code = 1
  payload.error = String(error)
  process.exitCode = 1
} finally {
  if (changed && source && original) {
    if ((await readFile(source)).equals(changed)) await writeFile(source, original)
    else payload.restore_error = 'Source changed concurrently; manual merge required'
  }
  const times = payload.samples.map((sample) => sample.wall_seconds).sort((a, b) => a - b)
  payload.successful_samples = times.length
  payload.median_seconds = times.length
    ? (times[Math.floor((times.length - 1) / 2)] + times[Math.ceil((times.length - 1) / 2)]) / 2
    : null
  payload.min_seconds = times[0] ?? null
  payload.max_seconds = times.at(-1) ?? null
  await mkdir(path.dirname(output), { recursive: true })
  await writeFile(output, JSON.stringify(payload, null, 2) + '\n')
  await writeFile(
    output.replace(/\.json$/, '.csv'),
    'sample,wall_seconds\n' +
      payload.samples.map((sample) => `${sample.sample},${sample.wall_seconds}\n`).join(''),
  )
  await browser.close()
}
