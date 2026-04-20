import type { BatchEventsPayload, BatchEventsResponse, BehaviorSession } from '@/types/api'
import { api } from './api'

export async function startSession(isEnrollment: boolean): Promise<BehaviorSession> {
  const { data } = await api.post<BehaviorSession>('/behavior/sessions/start/', {
    is_enrollment: isEnrollment,
    user_agent: navigator.userAgent,
    client_started_at: new Date().toISOString(),
  })
  return data
}

export async function endSession(token: string): Promise<void> {
  await api.post(`/behavior/sessions/${token}/end/`)
}

export async function postEvents(
  token: string,
  payload: BatchEventsPayload,
): Promise<BatchEventsResponse> {
  const { data } = await api.post<BatchEventsResponse>(
    `/behavior/sessions/${token}/events/`,
    payload,
  )
  return data
}
