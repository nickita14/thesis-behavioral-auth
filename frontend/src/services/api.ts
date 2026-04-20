import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  headers: { 'Content-Type': 'application/json' },
})

// On 403 from /auth/me (session expired) redirect to login.
// We use 403 because Django SessionAuthentication returns 403, not 401.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url: string = error.config?.url ?? ''
    if (status === 403 && !url.includes('/auth/')) {
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)
