const path = require('path');
const fs = require('fs');

/**
 * Application Configuration
 * Loads and manages desktop app configuration
 */
class AppConfig {
  constructor() {
    this.config = this._loadConfig();
  }

  /**
   * Load configuration from config file
   * @private
   */
  _loadConfig() {
    // Try to load from project root config
    const configPath = path.join(__dirname, '../../../config/desktop.yaml');

    if (fs.existsSync(configPath)) {
      // TODO: Implement YAML parsing
      console.log('[AppConfig] Loading from', configPath);
    }

    // Default configuration
    return {
      application: {
        name: 'Anima Desktop',
        version: '1.0.0'
      },

      windows: {
        live2d: {
          width: 400,
          height: 600,
          transparent: true,
          frame: false,
          alwaysOnTop: true,
          resizable: true,
          skipTaskbar: false,
          title: 'Anima Live2D'
        },

        chat: {
          width: 380,
          height: 500,
          resizable: true,
          title: 'Anima Chat'
        }
      },

      model: {
        // Relative path from renderer/live2d/ to public/live2d/
        defaultPath: '../../public/live2d/haru/haru_greeter_t03.model3.json',
        scale: 1.0,
        position: {
          x: 0,
          y: 0
        }
      },

      lipSync: {
        enabled: true,
        visemeMode: true,
        sensitivity: 2.5,
        smoothing: 0.3
      },

      actions: {
        queue: {
          maxSize: 120,
          overflowPolicy: 'drop_oldest'
        },
        cooldownMs: 250
      },

      backend: {
        wsUrl: 'ws://localhost:12394',
        rpcPort: 17373
      }
    };
  }

  /**
   * Get configuration value by path
   * @param {string} path - Dot-notation path (e.g., 'windows.live2d.width')
   * @param {*} defaultValue - Default value if path not found
   * @returns {*} Configuration value
   */
  get(path, defaultValue = null) {
    const keys = path.split('.');
    let value = this.config;

    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key];
      } else {
        return defaultValue;
      }
    }

    return value;
  }

  /**
   * Get Live2D window configuration
   * @returns {Object} Live2D window config
   */
  getLive2DWindowConfig() {
    return this.config.windows.live2d;
  }

  /**
   * Get chat window configuration
   * @returns {Object} Chat window config
   */
  getChatWindowConfig() {
    return this.config.windows.chat;
  }

  /**
   * Get model configuration
   * @returns {Object} Model config
   */
  getModelConfig() {
    return this.config.model;
  }

  /**
   * Get backend WebSocket URL
   * @returns {string} WebSocket URL
   */
  getWsUrl() {
    return this.config.backend.wsUrl;
  }
}

module.exports = new AppConfig();
