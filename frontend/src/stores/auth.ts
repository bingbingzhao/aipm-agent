import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { apiClient } from '@/api/client'

interface User {
  id: string
  email: string
  username: string
  created_at: string
}

const TOKEN_KEY = 'aipm_token'
const USER_KEY = 'aipm_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<User | null>(
    localStorage.getItem(USER_KEY)
      ? JSON.parse(localStorage.getItem(USER_KEY)!)
      : null
  )

  const isAuthenticated = computed(() => !!token.value)

  function setAuth(newToken: string, newUser: User) {
    token.value = newToken
    user.value = newUser
    localStorage.setItem(TOKEN_KEY, newToken)
    localStorage.setItem(USER_KEY, JSON.stringify(newUser))
  }

  function clearAuth() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  async function register(email: string, username: string, password: string) {
    const res = await apiClient.post('/api/auth/register', { email, username, password })
    setAuth(res.access_token, res.user)
    return res
  }

  async function login(email: string, password: string) {
    const res = await apiClient.post('/api/auth/login', { email, password })
    setAuth(res.access_token, res.user)
    return res
  }

  function logout() {
    clearAuth()
  }

  async function fetchMe() {
    try {
      const me = await apiClient.get('/api/auth/me')
      user.value = me
      localStorage.setItem(USER_KEY, JSON.stringify(me))
      return me
    } catch {
      clearAuth()
      return null
    }
  }

  return { token, user, isAuthenticated, register, login, logout, fetchMe, setAuth, clearAuth }
})
