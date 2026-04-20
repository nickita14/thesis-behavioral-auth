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
  session_token: string
  started_at: string
  ended_at: string | null
  is_enrollment: boolean
  ip_address: string
  counts?: {
    keystrokes: number
    mouse_events: number
  }
}

export interface StartSessionPayload {
  is_enrollment: boolean
  user_agent: string
  client_started_at: string
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
  accepted: { keystrokes: number; mouse: number }
  duplicates: { keystrokes: number; mouse: number }
}

export interface ApiError {
  detail?: string
  [field: string]: string | string[] | undefined
}
