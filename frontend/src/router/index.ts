/**
 * 路由配置
 * / → 路网列表页
 * /network/:id → 路网工作台
 */
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'network-list',
      component: () => import('../views/NetworkList.vue')
    },
    {
      path: '/network/:id',
      name: 'network-workspace',
      component: () => import('../views/NetworkWorkspace.vue'),
      props: true
    }
  ]
})

export default router
