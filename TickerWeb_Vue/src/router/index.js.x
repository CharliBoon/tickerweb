import { createRouter, createWebHistory } from 'vue-router'
import Cone-Src from '../components/TickerVTK.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/cone',
      name: 'cone',
      component: Cone-Src
    },
  ]
})

export default router