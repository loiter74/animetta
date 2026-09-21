import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import EarthWorkspace from './EarthWorkspace.vue'

const runtime = vi.hoisted(() => ({ mount: vi.fn() }))
vi.mock('./mount', () => ({ mountEarth: runtime.mount }))
afterEach(() => {
  vi.clearAllMocks()
})

function mountWorkspace() {
  return mount(EarthWorkspace, {
    global: { stubs: { EarthAvatar: { template: '<div data-testid="avatar" />' } } },
  })
}

describe('Earth workspace composition', () => {
  it('retains text/map controls with the avatar disabled and releases owned resources on exit', async () => {
    const controller = { dispose: vi.fn(), pause: vi.fn(), submit: vi.fn() }
    runtime.mount.mockResolvedValue(controller)
    const wrapper = mountWorkspace()
    await flushPromises()
    const toggles = wrapper.findAll('input[type="checkbox"]')
    await toggles[0].setValue(false)
    expect(wrapper.find('[data-testid="avatar"]').exists()).toBe(false)
    await wrapper.get('input[aria-label="告诉 Animetta 你的线索"]').setValue('上海')
    await wrapper.get('form').trigger('submit')
    expect(controller.submit).toHaveBeenCalledWith('上海')
    const signal = runtime.mount.mock.calls[0][0].signal as AbortSignal
    wrapper.unmount()
    expect(signal.aborted).toBe(true)
    expect(controller.dispose).toHaveBeenCalledTimes(1)
  })
  it('disposes a late initialized controller instead of reopening a closed workspace', async () => {
    let resolve!: (controller: { dispose(): void }) => void
    runtime.mount.mockImplementation(
      () =>
        new Promise((value) => {
          resolve = value
        }),
    )
    const wrapper = mountWorkspace()
    wrapper.unmount()
    const dispose = vi.fn()
    resolve({ dispose })
    await flushPromises()
    expect(dispose).toHaveBeenCalledTimes(1)
  })
})
