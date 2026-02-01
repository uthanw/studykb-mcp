import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('./views/CategoryManagerView.vue'),
    },
    {
      path: '/progress',
      name: 'progress',
      component: () => import('./views/ProgressView.vue'),
    },
    {
      path: '/progress/:category',
      name: 'progress-detail',
      component: () => import('./views/ProgressDetailView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('./views/SettingsView.vue'),
    },
  ],
})

export default router
