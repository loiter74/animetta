import { defineConfig, presetUno, presetIcons, transformerDirectives } from 'unocss'

export default defineConfig({
  presets: [
    presetUno({
      dark: 'class'
    }),
    presetIcons({
      scale: 1.2
    })
  ],
  transformers: [
    transformerDirectives()
  ],
  theme: {
    colors: {
      // 日系二次元主题色
      'c': {
        // 背景
        'bg': '#1a1028',
        'surface': '#241538',
        'panel': '#2d1b45',
        'card': '#36205a',
        // 文字
        'text': '#e8e0f0',
        'text-dim': '#9b8bb0',
        'text-muted': '#6b5a80',
        // 强调色 - 粉紫色系
        'accent': '#e879a8',
        'accent-hover': '#f090c0',
        'accent-soft': 'rgba(232, 121, 168, 0.15)',
        // 辅助色
        'blue': '#7c8cf5',
        'mint': '#6ee7b7',
        'gold': '#f5c872',
        // 状态色
        'success': '#4ade80',
        'warning': '#fbbf24',
        'error': '#f87171',
        // 边框
        'border': 'rgba(255, 255, 255, 0.08)',
        'border-accent': 'rgba(232, 121, 168, 0.3)',
        // 用户/AI 消息
        'user-bubble': 'rgba(124, 140, 245, 0.2)',
        'ai-bubble': 'rgba(232, 121, 168, 0.15)',
      }
    },
    fontFamily: {
      sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Hiragino Sans", "Noto Sans SC", "Microsoft YaHei", sans-serif'
    }
  },
  shortcuts: {
    // Glassmorphism 面板
    'glass': 'bg-$c-surface/70 backdrop-blur-xl border border-$c-border rounded-2xl',
    'glass-strong': 'bg-$c-surface/85 backdrop-blur-2xl border border-$c-border rounded-2xl',
    // 按钮
    'btn-accent': 'bg-$c-accent hover:bg-$c-accent-hover text-white rounded-xl px-4 py-2 transition-all duration-200 active:scale-95',
    'btn-ghost': 'bg-transparent hover:bg-$c-accent-soft text-$c-text-dim hover:text-$c-accent rounded-xl px-3 py-2 transition-all duration-200',
    // 动画
    'animate-fade-in': 'animate-[fadeIn_0.3s_ease]',
    'animate-slide-up': 'animate-[slideUp_0.3s_ease]',
  }
})
