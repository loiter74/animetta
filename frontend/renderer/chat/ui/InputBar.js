/**
 * InputBar - Input field and send button management
 */

export class InputBar {
  constructor(inputElement, sendBtn, onSend) {
    this.input = inputElement;
    this.sendBtn = sendBtn;
    this.onSend = onSend;
    
    this._setupEventListeners();
  }

  _setupEventListeners() {
    // Send button click
    this.sendBtn.addEventListener('click', () => this._handleSend());

    // Enter to send, Shift+Enter for new line
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this._handleSend();
      }
    });

    // Auto-resize textarea
    this.input.addEventListener('input', () => this.resize());
  }

  _handleSend() {
    const text = this.getValue().trim();
    if (text && this.onSend) {
      this.onSend(text);
      this.clear();
    }
  }

  /**
   * Get input value
   */
  getValue() {
    return this.input.value;
  }

  /**
   * Clear input
   */
  clear() {
    this.input.value = '';
    this.resize();
  }

  /**
   * Focus input
   */
  focus() {
    this.input.focus();
  }

  /**
   * Resize textarea to fit content
   */
  resize() {
    this.input.style.height = 'auto';
    this.input.style.height = Math.min(this.input.scrollHeight, 120) + 'px';
  }
}
