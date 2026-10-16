import { defineConfig, presetUno, presetIcons, transformerDirectives } from 'unocss'

export default defineConfig({
  presets: [
    presetUno({
      dark: 'class',
    }),
    presetIcons({
      scale: 1.2,
    }),
  ],
  transformers: [transformerDirectives()],
  theme: {
    // Responsive breakpoints — aligned with useMobile composable
    // sm:640 md:768 lg:1024 xl:1280 2xl:1536 (UnoCSS defaults, explicit for clarity)
    breakpoints: {
      sm: '640px',
      md: '768px',
      lg: '1024px',
      xl: '1280px',
      '2xl': '1536px',
    },
    colors: {
      // 日系二次元主题色 — CSS custom properties 支持亮色/暗色双模式
      // Hex-backed colors use the `rgb(var(--c-X-rgb) / <alpha-value>)` form so
      // UnoCSS opacity modifiers (bg-c-accent/20) inject real alpha. The plain
      // `var()` form dropped `/NN`, making tinted backgrounds identical to the
      // full-strength color and hiding same-color text/icons (e.g. play ▶).
      'c-bg': 'rgb(var(--c-bg-rgb) / <alpha-value>)',
      'c-surface': 'rgb(var(--c-surface-rgb) / <alpha-value>)',
      'c-panel': 'rgb(var(--c-panel-rgb) / <alpha-value>)',
      'c-card': 'rgb(var(--c-card-rgb) / <alpha-value>)',
      'c-text': 'rgb(var(--c-text-rgb) / <alpha-value>)',
      'c-text-dim': 'rgb(var(--c-text-dim-rgb) / <alpha-value>)',
      // c-text-secondary is a legacy alias used across many components; point
      // it at the same channels as c-text-dim so those 37 call sites pick up
      // the shared neutral secondary color instead of resolving to nothing.
      'c-text-secondary': 'rgb(var(--c-text-dim-rgb) / <alpha-value>)',
      'c-text-muted': 'rgb(var(--c-text-muted-rgb) / <alpha-value>)',
      'c-accent': 'rgb(var(--c-accent-rgb) / <alpha-value>)',
      'c-accent-hover': 'rgb(var(--c-accent-hover-rgb) / <alpha-value>)',
      'c-on-accent': 'rgb(var(--c-on-accent-rgb) / <alpha-value>)',
      'c-accent-soft': 'var(--c-accent-soft)',
      'c-blue': 'rgb(var(--c-blue-rgb) / <alpha-value>)',
      'c-mint': 'rgb(var(--c-mint-rgb) / <alpha-value>)',
      'c-gold': 'rgb(var(--c-gold-rgb) / <alpha-value>)',
      'c-violet': 'rgb(var(--c-violet-rgb) / <alpha-value>)',
      'c-violet-soft': 'var(--c-violet-soft)',
      'c-violet-glow': 'var(--c-violet-glow)',
      'c-success': 'rgb(var(--c-success-rgb) / <alpha-value>)',
      'c-warning': 'rgb(var(--c-warning-rgb) / <alpha-value>)',
      'c-error': 'rgb(var(--c-error-rgb) / <alpha-value>)',
      'c-border': 'var(--c-border)',
      'c-border-accent': 'var(--c-border-accent)',
      'c-border-strong': 'var(--c-border-strong)',
      'c-user-bubble': 'var(--c-user-bubble)',
      'c-ai-bubble': 'var(--c-ai-bubble)',
      'c-glow': 'var(--c-glow)',
      'c-glow-soft': 'var(--c-glow-soft)',
    },
    fontFamily: {
      sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Hiragino Sans", "Noto Sans SC", "Microsoft YaHei", sans-serif',
    },
    boxShadow: {
      panel: 'var(--shadow-panel)',
      control: 'var(--shadow-control)',
    },
    easing: {
      'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
      'back-soft': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
    },
  },
  shortcuts: {
    // A quiet surface hierarchy shared by both themes.
    glass: 'bg-c-surface/95 backdrop-blur-lg rounded-xl border border-c-border shadow-panel',
    'glass-strong': 'bg-c-panel/95 backdrop-blur-xl rounded-xl border border-c-border shadow-panel',
    // One control grammar: 36px, explicit hierarchy, visible keyboard focus.
    'btn-base':
      'inline-flex min-h-9 items-center justify-center gap-2 whitespace-nowrap rounded-xl border border-transparent px-3.5 py-1.5 text-xs font-semibold leading-4 cursor-pointer transition-colors duration-150 ease-out-expo focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-c-accent focus-visible:ring-offset-2 focus-visible:ring-offset-c-bg active:translate-y-px disabled:cursor-not-allowed disabled:opacity-45 disabled:active:translate-y-0',
    'btn-accent':
      'btn-base bg-c-accent text-c-on-accent hover:bg-c-accent-hover disabled:hover:bg-c-accent shadow-control',
    'btn-secondary':
      'btn-base border-c-border bg-c-panel text-c-text-dim hover:border-c-border-strong hover:bg-c-card hover:text-c-text disabled:hover:bg-c-panel',
    'btn-ghost':
      'btn-base bg-transparent text-c-text-dim hover:bg-c-card hover:text-c-text disabled:hover:bg-transparent',
    'btn-danger': 'btn-base bg-transparent text-c-error hover:bg-c-error/10',
    'btn-icon': 'btn-ghost h-9 w-9 min-w-9 shrink-0 p-0',
    'control-field':
      'h-9 min-w-0 rounded-xl border border-c-border bg-c-panel px-3 text-xs text-c-text leading-5 transition-colors duration-150 ease-out-expo placeholder:text-c-text-muted hover:border-c-border-strong focus:outline-none focus:ring-2 focus:ring-c-accent/25 focus:border-c-accent',
    'input-field': 'control-field',
    'segmented-control':
      'inline-flex items-center gap-1 rounded-xl border border-c-border bg-c-bg/65 p-1',
    'segment-option':
      'btn-base min-h-7 rounded-lg px-3 py-1 leading-4 font-medium bg-transparent text-c-text-dim hover:text-c-text aria-pressed:bg-c-panel aria-pressed:text-c-text aria-pressed:shadow-control',
    'workspace-body':
      'flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto p-4 sm:p-6 lg:overflow-hidden',
    'workspace-title': 'text-xl font-semibold leading-7 tracking-tight text-c-text',
    'workspace-copy': 'mt-1 max-w-2xl text-xs leading-5 text-c-text-dim',
    // 渐变
    'gradient-accent': 'bg-gradient-to-br from-c-accent to-c-accent-hover',
    'gradient-accent-soft': 'bg-gradient-to-br from-c-accent/20 to-c-blue/20',
    // 动画
    'animate-fade-in': 'animate-[fadeIn_var(--d-base)_var(--ease-out-expo)]',
    'animate-slide-up': 'animate-[slideUp_var(--d-slow)_var(--ease-out-expo)]',
    'animate-slide-in-right': 'animate-[slideInRight_var(--d-slow)_var(--ease-out-expo)]',
    'animate-slide-out-right': 'animate-[slideOutRight_var(--d-slow)_var(--ease-out-expo)]',
    // Mobile utilities
    'touch-manipulation': '[touch-action:manipulation]',
    'safe-bottom': 'pb-[env(safe-area-inset-bottom)]',
    'safe-top': 'pt-[env(safe-area-inset-top)]',
  },
})
