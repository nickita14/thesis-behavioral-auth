import type { LoginPayload, RegisterPayload, User } from '@/types/api'
import { api } from './api'

/** Sets the csrftoken cookie. Must be called once before any POST. */
export async function ensureCsrf(): Promise<void> {
  await api.get('/auth/csrf/')
}

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await api.post<User>('/auth/register/', payload)
  return data
}

export async function login(payload: LoginPayload): Promise<User> {
  const { data } = await api.post<User>('/auth/login/', payload)
  return data
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout/')
}

/** Returns the current user or null if the session has expired. */
export async function getCurrentUser(): Promise<User | null> {
  try {
    const { data } = await api.get<User>('/auth/me/')
    return data
  } catch {
    return null
  }
}
