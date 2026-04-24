import type {
  BatchEventsPayload,
  BatchEventsResponse,
  BehaviorSession,
  BehaviorSummary,
} from '@/types/api'
import { api } from './api'

type KeystrokeDataRow = NonNullable<BatchEventsPayload['keystrokes']>['data'][number]
type MouseDataRow = NonNullable<BatchEventsPayload['mouse']>['data'][number]

export async function startSession(isEnrollment: boolean): Promise<BehaviorSession> {
  const { data } = await api.post<BehaviorSession>('/behavior/sessions/', {
    is_enrollment: isEnrollment,
    context: {
      source: 'frontend-collector',
      user_agent: navigator.userAgent,
      client_started_at: new Date().toISOString(),
    },
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
  const keystrokes = payload.keystrokes?.data ?? []
  const mouse = payload.mouse?.data ?? []
  const [keystrokeResponse, mouseResponse] = await Promise.all([
    keystrokes.length
      ? api.post<{ created: number }>(
          `/behavior/sessions/${token}/keystrokes/`,
          { events: keystrokes.map(toKeystrokeEvents).flat() },
        )
      : Promise.resolve({ data: { created: 0 } }),
    mouse.length
      ? api.post<{ created: number }>(
          `/behavior/sessions/${token}/mouse/`,
          { events: mouse.map(toMouseEvent) },
        )
      : Promise.resolve({ data: { created: 0 } }),
  ])

  return {
    created: {
      keystrokes: keystrokeResponse.data.created,
      mouse: mouseResponse.data.created,
    },
  }
}

export async function getSummary(token: string): Promise<BehaviorSummary> {
  const { data } = await api.get<BehaviorSummary>(`/behavior/sessions/${token}/summary/`)
  return data
}

export function toKeystrokeEvents(row: KeystrokeDataRow) {
  const [clientId, category, down, up, flight] = row
  const dwell = Math.max(up - down, 0)
  const metadata = { client_id: clientId, key_category: category }
  return [
    {
      event_type: 'keydown',
      key_code: category,
      timestamp_ms: down,
      relative_time_ms: down,
      flight_time_ms: flight,
      metadata,
    },
    {
      event_type: 'keyup',
      key_code: category,
      timestamp_ms: up,
      relative_time_ms: up,
      dwell_time_ms: dwell,
      metadata,
    },
  ]
}

export function toMouseEvent(row: MouseDataRow) {
  const [clientId, eventType, timestamp, x, y, button, deltaX, deltaY] = row
  return {
    event_type: eventType,
    x,
    y,
    button: button ?? '',
    scroll_delta_x: deltaX,
    scroll_delta_y: deltaY,
    timestamp_ms: timestamp,
    relative_time_ms: timestamp,
    metadata: { client_id: clientId },
  }
}
