/**
 * MessageList - Message list rendering and scrolling
 */

export class MessageList {
  constructor(containerElement) {
    this.container = containerElement;
  }

  /**
   * Add message element to list
   */
  addMessage(message) {
    // Remove empty state
    const emptyState = this.container.querySelector('.empty-state');
    if (emptyState) {
      emptyState.remove();
    }

    const messageEl = this.createMessageElement(message);
    this.container.appendChild(messageEl);
    this.scrollToBottom();
  }

  /**
   * Update existing message
   */
  updateMessage(message) {
    const messageEl = document.querySelector(`[data-id="${message.id}"]`);
    if (!messageEl) {
      console.warn('[MessageList] Message element not found for id:', message.id);
      return false;
    }

    const contentEl = messageEl.querySelector('.message-content');
    if (contentEl) {
      contentEl.textContent = message.text;
      if (message.streaming) {
        contentEl.classList.add('streaming');
      } else {
        contentEl.classList.remove('streaming');
      }
    }
    this.scrollToBottom();
    return true;
  }

  /**
   * Create message element
   */
  createMessageElement(message) {
    const el = document.createElement('div');
    el.className = `message ${message.role}`;
    el.dataset.id = message.id;

    const content = document.createElement('div');
    content.className = 'message-content';
    if (message.streaming) {
      content.classList.add('streaming');
    }
    content.textContent = message.text;

    const meta = document.createElement('div');
    meta.className = 'message-meta';
    meta.textContent = new Date(message.timestamp).toLocaleTimeString();

    el.appendChild(content);
    el.appendChild(meta);

    return el;
  }

  /**
   * Scroll to bottom
   */
  scrollToBottom() {
    this.container.scrollTop = this.container.scrollHeight;
  }

  /**
   * Append child element
   */
  appendChild(element) {
    this.container.appendChild(element);
  }

  /**
   * Query selector
   */
  querySelector(selector) {
    return this.container.querySelector(selector);
  }
}
