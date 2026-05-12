import { createRouter, createMemoryHistory } from 'vue-router'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: () => import('../views/ChatPage.vue'),
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('../views/DashboardPage.vue'),
    },
    {
      path: '/meme-review',
      name: 'meme-review',
      component: () => import('../views/MemeReview.vue'),
    },
  ],
})

export default router
