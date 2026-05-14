import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TypingIndicator from '@/components/chat/TypingIndicator.vue'

describe('TypingIndicator', () => {
  it('renders three dots', () => {
    const wrapper = mount(TypingIndicator)
    const dots = wrapper.findAll('span.rounded-full')
    expect(dots).toHaveLength(3)
  })

  it('renders "思考中" text', () => {
    const wrapper = mount(TypingIndicator)
    expect(wrapper.text()).toContain('思考中')
  })

  it('renders without errors', () => {
    const wrapper = mount(TypingIndicator)
    expect(wrapper.exists()).toBe(true)
  })
})
