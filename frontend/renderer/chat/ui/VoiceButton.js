/**
 * VoiceButton - Voice input button state management
 */

export class VoiceButton {
  constructor(buttonElement, onStart, onStop) {
    this.button = buttonElement;
    this.onStart = onStart;
    this.onStop = onStop;
    this.isRecording = false;
    
    this._setupEventListeners();
  }

  _setupEventListeners() {
    this.button.addEventListener('click', () => this.toggle());
  }

  /**
   * Toggle recording state
   */
  async toggle() {
    if (this.isRecording) {
      await this.stop();
    } else {
      await this.start();
    }
  }

  /**
   * Start recording
   */
  async start() {
    if (this.onStart) {
      await this.onStart();
    }
    this.isRecording = true;
    this.button.classList.add('recording');
    // console.log('[VoiceButton] Recording started');
  }

  /**
   * Stop recording
   */
  async stop() {
    if (this.onStop) {
      await this.onStop();
    }
    this.isRecording = false;
    this.button.classList.remove('recording');
    // console.log('[VoiceButton] Recording stopped');
  }

  /**
   * Get recording state
   */
  getRecording() {
    return this.isRecording;
  }
}
