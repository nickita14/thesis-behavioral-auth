export interface User {
  id: number
  username: string
  email: string
  date_joined: string
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface BehaviorSession {
  id: string
  started_at: string
  is_enrollment: boolean
  context: Record<string, unknown>
}

export interface StartSessionPayload {
  is_enrollment: boolean
  context?: Record<string, unknown>
}

export type KeyCategory = 'letter' | 'digit' | 'special' | 'modifier'
export type MouseEventType = 'move' | 'click' | 'scroll'

export interface KeystrokeRow {
  client_id: string
  cat: KeyCategory
  down: number
  up: number
  flight: number | null
}

export interface MouseEventRow {
  client_id: string
  type: MouseEventType
  t: number
  x: number
  y: number
  btn: string | null
  dx: number | null
  dy: number | null
}

export interface BatchEventsPayload {
  schema_version: 1
  client_time: string
  keystrokes?: {
    fields: readonly ['client_id', 'cat', 'down', 'up', 'flight']
    data: ReadonlyArray<readonly [string, KeyCategory, number, number, number | null]>
  }
  mouse?: {
    fields: readonly ['client_id', 'type', 't', 'x', 'y', 'btn', 'dx', 'dy']
    data: ReadonlyArray<readonly [string, MouseEventType, number, number, number, string | null, number | null, number | null]>
  }
}

export interface BatchEventsResponse {
  created: {
    keystrokes: number
    mouse: number
  }
}

export interface BehaviorSummary {
  id: string
  duration_ms: number | null
  keystroke_count: number
  mouse_count: number
  is_enrollment: boolean
}

export interface ApiError {
  detail?: string
  [field: string]: string | string[] | undefined
}
