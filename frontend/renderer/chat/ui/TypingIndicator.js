/**
 * TypingIndicator - Typing animation management
 */

const TYPING_INDICATOR_ID = 'typing-indicator';

export class TypingIndicator {
  constructor(messageList) {
    this.messageList = messageList;
  }

  /**
   * Show typing indicator
   */
  show() {
    // Remove existing first
    this.hide();

    const indicator = document.createElement('div');
    indicator.className = 'message assistant typing';
    indicator.id = TYPING_INDICATOR_ID;

    const content = document.createElement('div');
    content.className = 'message-content';

    const dots = document.createElement('div');
    dots.className = 'typing-indicator';
    
    // Create dots programmatically (no innerHTML)
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('div');
      dot.className = 'typing-dot';
      dots.appendChild(dot);
    }

    content.appendChild(dots);
    indicator.appendChild(content);
    this.messageList.appendChild(indicator);

    this._scrollToBottom();
  }

  /**
   * Hide typing indicator
   */
  hide() {
    const indicator = document.getElementById(TYPING_INDICATOR_ID);
    if (indicator) {
      indicator.remove();
    }
  }

  _scrollToBottom() {
    this.messageList.scrollTop = this.messageList.scrollHeight;
  }
}
