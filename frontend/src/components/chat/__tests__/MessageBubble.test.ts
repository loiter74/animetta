import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageBubble from '@/components/chat/MessageBubble.vue'
import type { ChatMessage } from '@/types/chat'

function createMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'msg-1',
    role: 'user',
    text: 'Hello world',
    timestamp: Date.now(),
    status: 'complete',
    ...overrides,
  }
}

describe('MessageBubble', () => {
  it('renders user message with correct text', () => {
    const msg = createMessage({ role: 'user', text: 'Hello from user' })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    expect(wrapper.text()).toContain('Hello from user')
  })

  it('renders assistant message with correct text', () => {
    const msg = createMessage({ role: 'assistant', text: 'Hi, I am Anima!' })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    expect(wrapper.text()).toContain('Hi, I am Anima!')
  })

  it('positions user messages on the right (self-end)', () => {
    const msg = createMessage({ role: 'user', text: 'User message' })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    const container = wrapper.find('.self-end')
    expect(container.exists()).toBe(true)
  })

  it('positions assistant messages on the left (self-start)', () => {
    const msg = createMessage({ role: 'assistant', text: 'AI message' })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    const container = wrapper.find('.self-start')
    expect(container.exists()).toBe(true)
  })

  it('shows streaming cursor when status is streaming', () => {
    const msg = createMessage({ role: 'assistant', text: 'Streaming...', status: 'streaming' })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    // Streaming cursor is a span with class animate-blink
    const cursor = wrapper.find('.animate-blink')
    expect(cursor.exists()).toBe(true)
  })

  it('does not show streaming cursor when status is complete', () => {
    const msg = createMessage({ role: 'assistant', text: 'Complete message', status: 'complete' })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    const cursor = wrapper.find('.animate-blink')
    expect(cursor.exists()).toBe(false)
  })

  it('renders per-char streaming spans for assistant streaming', () => {
    const msg = createMessage({ role: 'assistant', text: 'Hi', status: 'streaming' })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    // Each character should be wrapped in a span inside .streaming-text
    const streamingText = wrapper.find('.streaming-text')
    expect(streamingText.exists()).toBe(true)
    const charSpans = streamingText.findAll('span')
    expect(charSpans.length).toBe(2) // one per character
    expect(charSpans[0].text()).toBe('H')
    expect(charSpans[1].text()).toBe('i')
  })

  it('renders full text directly for complete messages', () => {
    const msg = createMessage({ role: 'user', text: 'Full text', status: 'complete' })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    // For non-streaming, the text should be a direct child (not in streaming-text spans)
    const streamingText = wrapper.find('.streaming-text')
    expect(streamingText.exists()).toBe(false)
    expect(wrapper.text()).toContain('Full text')
  })

  it('shows timestamp', () => {
    const ts = 1700000000000
    const msg = createMessage({ timestamp: ts })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    // Timestamp is rendered via toLocaleTimeString
    expect(wrapper.text()).toContain(':')
  })

  it('renders empty text messages', () => {
    const msg = createMessage({ text: '' })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    expect(wrapper.exists()).toBe(true)
  })

  it('renders system messages on the left', () => {
    const msg = createMessage({ role: 'system', text: 'System notification' })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    // System messages are not user, so they should be self-start
    const container = wrapper.find('.self-start')
    expect(container.exists()).toBe(true)
  })

  it('applies streaming animation class', () => {
    const msg = createMessage({ role: 'assistant', text: 'text', status: 'streaming' })
    const wrapper = mount(MessageBubble, { props: { message: msg } })
    const bubble = wrapper.find('.streaming')
    expect(bubble.exists()).toBe(true)
  })
})
