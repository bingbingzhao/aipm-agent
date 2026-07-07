import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import ProjectView from '@/views/ProjectView.vue'
import AuthView from '@/views/AuthView.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: AuthView,
      meta: { public: true },
    },
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/project/:id',
      name: 'project',
      component: ProjectView,
      props: true,
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  // Public routes are always accessible
  if (to.meta.public) {
    // Already logged in → skip login page
    if (to.name === 'login' && auth.isAuthenticated) {
      return { path: '/' }
    }
    return true
  }
  // Protected routes require auth
  if (!auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
