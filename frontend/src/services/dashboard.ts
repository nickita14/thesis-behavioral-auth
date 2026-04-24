import type { DashboardData } from '@/types/api'
import { api } from './api'

export async function getDashboardData(): Promise<DashboardData> {
  const { data } = await api.get<DashboardData>('/behavior/dashboard/')
  return data
}
