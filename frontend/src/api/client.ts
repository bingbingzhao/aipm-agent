const BASE_URL = import.meta.env.VITE_API_URL || ''
const TOKEN_KEY = 'aipm_token'

async function request(method: string, path: string, body?: unknown) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }

  // Inject auth token if present
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const options: RequestInit = { method, headers }
  if (body) {
    options.body = JSON.stringify(body)
  }

  const res = await fetch(`${BASE_URL}${path}`, options)

  // Handle auth expiry: clear token and redirect to login
  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('aipm_user')
    if (!location.pathname.startsWith('/login')) {
      location.href = '/login'
    }
    throw new Error('登录已过期，请重新登录')
  }

  if (res.status === 204) return null
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export const apiClient = {
  get: (path: string) => request('GET', path),
  post: (path: string, body: unknown) => request('POST', path, body),
  patch: (path: string, body: unknown) => request('PATCH', path, body),
  delete: (path: string) => request('DELETE', path),
}
