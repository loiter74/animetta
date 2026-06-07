import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import WelcomeScreen from '@/components/chat/WelcomeScreen.vue'

// Mock gsap
vi.mock('gsap', () => ({
  gsap: {
    context: vi.fn((callback) => ({
      callback,
      revert: vi.fn()
    })),
    timeline: vi.fn(() => ({
      from: vi.fn().mockReturnThis()
    })),
    set: vi.fn()
  }
}))

// Mock SceneEffects
vi.mock('@/components/shared/SceneEffects.vue', () => ({
  default: {
    name: 'SceneEffects',
    template: '<div class="mock-scene-effects"></div>'
  }
}))

describe('WelcomeScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    })
  })

  it('renders hero section', () => {
    const wrapper = mount(WelcomeScreen)
    expect(wrapper.find('.h-screen').exists()).toBe(true)
  })

  it('renders title with accent dot', () => {
    const wrapper = mount(WelcomeScreen)
    const title = wrapper.find('h1')
    expect(title.exists()).toBe(true)
    expect(title.text()).toContain('Animetta')
    expect(wrapper.find('.text-c-accent').exists()).toBe(true)
  })

  it('renders subtitle', () => {
    const wrapper = mount(WelcomeScreen)
    expect(wrapper.text()).toContain('和我一起聊会儿天吧')
  })

  it('renders two CTA buttons', () => {
    const wrapper = mount(WelcomeScreen)
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBe(2)
    expect(buttons[0].text()).toBe('开始对话')
    expect(buttons[1].text()).toBe('了解更多')
  })

  it('emits dismiss when start chat clicked', async () => {
    const wrapper = mount(WelcomeScreen)
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('dismiss')).toBeTruthy()
  })

  it('renders background image', () => {
    const wrapper = mount(WelcomeScreen)
    const bg = wrapper.find('[style*="background-image"]')
    expect(bg.exists()).toBe(true)
  })

  it('renders SceneEffects', () => {
    const wrapper = mount(WelcomeScreen)
    expect(wrapper.find('.mock-scene-effects').exists()).toBe(true)
  })

  it('renders scroll hint', () => {
    const wrapper = mount(WelcomeScreen)
    expect(wrapper.find('.animate-bounce').exists()).toBe(true)
  })

  it('has responsive classes', () => {
    const wrapper = mount(WelcomeScreen)
    expect(wrapper.find('.md\\:text-6xl').exists()).toBe(true)
    expect(wrapper.find('.lg\\:text-7xl').exists()).toBe(true)
  })
})
