import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/Dashboard.vue')
    },
    {
      path: '/network',
      name: 'network',
      component: () => import('../views/NetworkEditor.vue')
    },
    {
      path: '/simulation',
      name: 'simulation',
      component: () => import('../views/Simulation.vue')
    },
    {
      path: '/optimization',
      name: 'optimization',
      component: () => import('../views/Optimization.vue')
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: () => import('../views/Analysis.vue')
    }
  ]
})

export default router
