import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/catalog',
      name: 'catalog',
      component: () => import('../views/CatalogView.vue')
    },
    {
      path: '/components/:slug',
      name: 'component',
      component: () => import('../views/ComponentView.vue')
    },
    {
      path: '/stacks',
      name: 'stacks',
      component: () => import('../views/StacksView.vue')
    }
  ]
})

export default router