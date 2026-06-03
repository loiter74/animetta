import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import 'virtual:uno.css'
import './styles/animations.css'
import './styles/themes.css'

// Theme initialization: localStorage > prefers-color-scheme > dark fallback
const STORAGE_KEY = 'animetta-theme'
const saved = localStorage.getItem(STORAGE_KEY)
if (saved === 'light' || saved === 'dark') {
  document.documentElement.className = `theme-${saved}`
} else if (window.matchMedia('(prefers-color-scheme: light)').matches) {
  document.documentElement.className = 'theme-light'
} else {
  document.documentElement.className = 'theme-dark'
}

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount('#app')
