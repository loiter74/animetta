// @vitest-environment node

import { access, readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { resolveCandidateModelProfile } from '../src/review/candidate-model'
import type { Live2DModelProfile } from '../src/shared/live2d/modelProfile'

it('standalone live page declares the existing favicon instead of requesting favicon.ico', async () => {
  const html = await readFile(resolve(process.cwd(), 'live.html'), 'utf8')

  expect(html).toMatch(/<link rel="icon" href="\/favicon\.svg"\s*\/>/)
})

it('uses the live page as the only TTS failover visual surface', async () => {
  const viteConfig = await readFile(resolve(process.cwd(), 'vite.config.ts'), 'utf8')

  expect(viteConfig).not.toContain('ttsFailover:')
  await expect(access(resolve(process.cwd(), 'tts-failover.html'))).rejects.toMatchObject({
    code: 'ENOENT',
  })
})

it('uses live.html as the only runtime live surface', async () => {
  const electronMain = await readFile(resolve(process.cwd(), 'electron/main.cjs'), 'utf8')
  const router = await readFile(resolve(process.cwd(), 'src/router/index.ts'), 'utf8')

  expect(electronMain).toContain("mainWindow.loadURL('http://localhost:3000/live.html')")
  expect(electronMain).not.toContain('/live-stream')
  expect(router).not.toContain('/live-stream')
  await expect(
    access(resolve(process.cwd(), 'src/views/LiveStreamPage.vue')),
  ).rejects.toMatchObject({
    code: 'ENOENT',
  })
})

describe('resolveCandidateModelProfile', () => {
  const profile: Live2DModelProfile = {
    id: 'candidate-review-base',
    modelUrl: '/live2d/whale-maid-v1/whale-maid-v1.model3.json',
    mouthParameters: ['ParamMouthOpenY'],
    performance: { resolve: () => [] },
    framing: { scale: 0.9, x: 0.5, y: 0.46 },
    semanticMotions: { planning: { group: 'Nod', index: 0 } },
  }
  const candidateSearch = (model?: string): URLSearchParams =>
    new URLSearchParams({ review: '1', media: 'muted', ...(model === undefined ? {} : { model }) })

  it('overrides only the model url when both review gates pass', () => {
    const candidate = '/.zcode/candidate-b/model.model3.json'
    const overridden = resolveCandidateModelProfile(profile, candidateSearch(candidate))

    expect(overridden).not.toBe(profile)
    expect(overridden).toEqual({ ...profile, modelUrl: candidate })
    expect(profile.modelUrl).toBe('/live2d/whale-maid-v1/whale-maid-v1.model3.json')
  })

  it('accepts one or more strict .zcode directory segments', () => {
    for (const candidate of [
      '/.zcode/dir/model.model3.json',
      '/.zcode/a/b-v2/c_d.model3.json',
      '/.zcode/Candidates-2026/Whale-Maid_v3/final.model3.json',
    ]) {
      expect(resolveCandidateModelProfile(profile, candidateSearch(candidate)).modelUrl).toBe(
        candidate,
      )
    }
  })

  it('keeps the exact profile reference when any gate is missing', () => {
    const gated = [
      new URLSearchParams(),
      new URLSearchParams({ media: 'muted', model: '/.zcode/dir/model.model3.json' }),
      new URLSearchParams({ review: '1', model: '/.zcode/dir/model.model3.json' }),
      new URLSearchParams({ review: '0', media: 'muted', model: '/.zcode/dir/model.model3.json' }),
      new URLSearchParams({
        review: 'true',
        media: 'muted',
        model: '/.zcode/dir/model.model3.json',
      }),
      new URLSearchParams({ review: '1', media: 'audio', model: '/.zcode/dir/model.model3.json' }),
      candidateSearch(),
    ]
    for (const search of gated) {
      expect(resolveCandidateModelProfile(profile, search)).toBe(profile)
    }
  })

  it('keeps the exact profile reference for candidate paths outside the .zcode allowlist', () => {
    const rejected = [
      'https://assets.example.com/model.model3.json',
      'http://127.0.0.1:8767/.zcode/dir/model.model3.json',
      '//assets.example.com/.zcode/dir/model.model3.json',
      '/live2d/mao/Mao.model3.json',
      '.zcode/dir/model.model3.json',
      '/.zcode/model.model3.json',
      '/.zcode//dir/model.model3.json',
      '/.zcode/dir//model.model3.json',
      '/.zcode/../live2d/mao/Mao.model3.json',
      '/.zcode/dir/../../secret/model.model3.json',
      '/.zcode/dir/model.model3.json?token=1',
      '/.zcode/dir/model.model3.json#frag',
      '/.zcode/dir\\model.model3.json',
      '\\\\.zcode\\dir\\model.model3.json',
      '/.zcode/dir/model.v2.model3.json',
      '/.zcode/dir/model.model3.json/',
      '/.zcode/dir/model.model3.json\n',
      '/.zcode/目录/model.model3.json',
    ]
    for (const model of rejected) {
      expect(resolveCandidateModelProfile(profile, candidateSearch(model))).toBe(profile)
    }
  })

  it('rejects percent-encoded traversal after URLSearchParams decoding', () => {
    expect(new URLSearchParams('model=/.zcode/%2e%2e/x.model3.json').get('model')).toBe(
      '/.zcode/../x.model3.json',
    )
    for (const query of [
      'review=1&media=muted&model=/.zcode/%2e%2e/x.model3.json',
      'review=1&media=muted&model=/.zcode/%252e%252e/x.model3.json',
      'review=1&media=muted&model=/.zcode/%2e%2e%2f%2e%2e%2fsecret/x.model3.json',
    ]) {
      expect(resolveCandidateModelProfile(profile, new URLSearchParams(query))).toBe(profile)
    }
  })
})
