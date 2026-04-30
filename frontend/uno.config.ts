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
      // 日系二次元主题色（扁平结构，避免 UnoCSS 多层嵌套的 hyphen 歧义）
      'c-bg': '#1a1028',
      'c-surface': '#241538',
      'c-panel': '#2d1b45',
      'c-card': '#36205a',
      'c-text': '#e8e0f0',
      'c-text-dim': '#9b8bb0',
      'c-text-muted': '#6b5a80',
      'c-accent': '#e879a8',
      'c-accent-hover': '#f090c0',
      'c-accent-soft': 'rgba(232, 121, 168, 0.15)',
      'c-blue': '#7c8cf5',
      'c-mint': '#6ee7b7',
      'c-gold': '#f5c872',
      'c-success': '#4ade80',
      'c-warning': '#fbbf24',
      'c-error': '#f87171',
      'c-border': 'rgba(255, 255, 255, 0.08)',
      'c-border-accent': 'rgba(232, 121, 168, 0.3)',
      'c-user-bubble': 'rgba(124, 140, 245, 0.2)',
      'c-ai-bubble': 'rgba(232, 121, 168, 0.15)',
      'c-glow': 'rgba(232, 121, 168, 0.4)',
      'c-glow-soft': 'rgba(232, 121, 168, 0.15)',
    },
    fontFamily: {
      sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Hiragino Sans", "Noto Sans SC", "Microsoft YaHei", sans-serif'
    }
  },
  shortcuts: {
    // Glassmorphism 面板
    'glass': 'bg-c-surface/70 backdrop-blur-xl border border-c-border rounded-2xl',
    'glass-strong': 'bg-c-surface/85 backdrop-blur-2xl border border-c-border rounded-2xl',
    // 按钮
    'btn-accent': 'bg-c-accent hover:bg-c-accent-hover text-white rounded-xl px-4 py-2 transition-all duration-200 active:scale-95',
    'btn-ghost': 'bg-transparent hover:bg-c-accent-soft text-c-text-dim hover:text-c-accent rounded-xl px-3 py-2 transition-all duration-200',
    // 渐变
    'gradient-accent': 'bg-gradient-to-br from-c-accent to-c-accent-hover',
    'gradient-accent-soft': 'bg-gradient-to-br from-c-accent/20 to-c-blue/20',
    // 动画
    'animate-fade-in': 'animate-[fadeIn_0.3s_ease]',
    'animate-slide-up': 'animate-[slideUp_0.3s_ease]',
    'animate-slide-in-right': 'animate-[slideInRight_0.3s_cubic-bezier(0.16,1,0.3,1)]',
    'animate-slide-out-right': 'animate-[slideOutRight_0.25s_ease-in]',
  }
})
