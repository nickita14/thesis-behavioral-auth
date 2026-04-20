import type { KeyCategory, KeystrokeRow, MouseEventRow, MouseEventType } from '@/types/api'
import { endSession, postEvents, startSession } from './behavior'

const BATCH_SIZE_THRESHOLD = 100
const BATCH_TIME_MS = 5000
const MOUSE_THROTTLE_MS = 50

function categorizeKey(key: string): KeyCategory {
  if (/^[a-zA-Z]$/.test(key)) return 'letter'
  if (/^[0-9]$/.test(key)) return 'digit'
  if (['Shift', 'Control', 'Alt', 'Meta'].includes(key)) return 'modifier'
  return 'special'
}

class BehaviorCollector {
  private sessionToken: string | null = null
  private sessionStart = 0

  private keystrokeBuffer: KeystrokeRow[] = []
  private mouseBuffer: MouseEventRow[] = []

  private lastKeyUpAt: number | null = null
  private lastMouseMoveAt = 0
  private flushTimer: ReturnType<typeof setTimeout> | null = null
  private retryTimer: ReturnType<typeof setTimeout> | null = null
  private pendingRetry: { ks: KeystrokeRow[]; ms: MouseEventRow[] } | null = null

  private listening = false

  // ── bound handlers (needed for removeEventListener) ───────────────────────

  private readonly onKeyDown = (e: KeyboardEvent): void => {
    if (!this.sessionToken) return
    const now = this.now()
    const category = categorizeKey(e.key)
    const flight = this.lastKeyUpAt !== null ? now - this.lastKeyUpAt : null

    this.keystrokeBuffer.push({
      client_id: crypto.randomUUID(),
      cat: category,
      down: now,
      up: 0, // filled in onKeyUp
      flight,
    })
    this.scheduleFlushIfNeeded()
  }

  private readonly onKeyUp = (e: KeyboardEvent): void => {
    if (!this.sessionToken) return
    const now = this.now()
    this.lastKeyUpAt = now

    // Find the matching keydown entry (last unmatched keystroke with same category)
    const category = categorizeKey(e.key)
    for (let i = this.keystrokeBuffer.length - 1; i >= 0; i--) {
      if (this.keystrokeBuffer[i].cat === category && this.keystrokeBuffer[i].up === 0) {
        this.keystrokeBuffer[i] = { ...this.keystrokeBuffer[i], up: now }
        break
      }
    }
  }

  private readonly onMouseMove = (e: MouseEvent): void => {
    if (!this.sessionToken) return
    const now = this.now()
    if (now - this.lastMouseMoveAt < MOUSE_THROTTLE_MS) return
    this.lastMouseMoveAt = now

    this.mouseBuffer.push({
      client_id: crypto.randomUUID(),
      type: 'move',
      t: now,
      x: e.clientX,
      y: e.clientY,
      btn: null,
      dx: null,
      dy: null,
    })
    this.scheduleFlushIfNeeded()
  }

  private readonly onClick = (e: MouseEvent): void => {
    if (!this.sessionToken) return
    const buttonMap: Record<number, string> = { 0: 'left', 1: 'middle', 2: 'right' }
    this.mouseBuffer.push({
      client_id: crypto.randomUUID(),
      type: 'click' as MouseEventType,
      t: this.now(),
      x: e.clientX,
      y: e.clientY,
      btn: buttonMap[e.button] ?? 'unknown',
      dx: null,
      dy: null,
    })
    this.scheduleFlushIfNeeded()
  }

  private readonly onWheel = (e: WheelEvent): void => {
    if (!this.sessionToken) return
    this.mouseBuffer.push({
      client_id: crypto.randomUUID(),
      type: 'scroll' as MouseEventType,
      t: this.now(),
      x: e.clientX,
      y: e.clientY,
      btn: null,
      dx: Math.round(e.deltaX),
      dy: Math.round(e.deltaY),
    })
    this.scheduleFlushIfNeeded()
  }

  private readonly onBeforeUnload = (): void => {
    if (!this.sessionToken) return
    const payload = this.buildPayload()
    if (!payload) return

    // fetch with keepalive supports headers (unlike sendBeacon)
    const csrfToken = this.getCsrfToken()
    void fetch(`/api/behavior/sessions/${this.sessionToken}/events/`, {
      method: 'POST',
      keepalive: true,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(payload),
    })
    this.keystrokeBuffer = []
    this.mouseBuffer = []
  }

  // ── public API ─────────────────────────────────────────────────────────────

  async startSession(isEnrollment: boolean): Promise<void> {
    const session = await startSession(isEnrollment)
    this.sessionToken = session.session_token
    this.sessionStart = Date.now()
    this.lastKeyUpAt = null
    this.keystrokeBuffer = []
    this.mouseBuffer = []
    this.scheduleTimer()
  }

  async endSession(): Promise<void> {
    if (!this.sessionToken) return
    await this.flush()
    await endSession(this.sessionToken)
    this.sessionToken = null
    this.clearTimer()
  }

  start(): void {
    if (this.listening) return
    this.listening = true
    document.addEventListener('keydown', this.onKeyDown)
    document.addEventListener('keyup', this.onKeyUp)
    document.addEventListener('mousemove', this.onMouseMove)
    document.addEventListener('click', this.onClick)
    document.addEventListener('wheel', this.onWheel, { passive: true })
    window.addEventListener('beforeunload', this.onBeforeUnload)
  }

  stop(): void {
    if (!this.listening) return
    this.listening = false
    document.removeEventListener('keydown', this.onKeyDown)
    document.removeEventListener('keyup', this.onKeyUp)
    document.removeEventListener('mousemove', this.onMouseMove)
    document.removeEventListener('click', this.onClick)
    document.removeEventListener('wheel', this.onWheel)
    window.removeEventListener('beforeunload', this.onBeforeUnload)
    this.clearTimer()
  }

  async flush(): Promise<void> {
    if (!this.sessionToken) return

    // Only send keystrokes that have been matched (up !== 0)
    const ks = this.keystrokeBuffer.filter((k) => k.up !== 0)
    const ms = [...this.mouseBuffer]
    if (ks.length === 0 && ms.length === 0) return

    this.keystrokeBuffer = this.keystrokeBuffer.filter((k) => k.up === 0)
    this.mouseBuffer = []

    try {
      const payload = this.buildPayloadFromBuffers(ks, ms)
      if (payload) await postEvents(this.sessionToken, payload)
      this.pendingRetry = null
    } catch {
      // Restore events for retry
      this.keystrokeBuffer = [...ks, ...this.keystrokeBuffer]
      this.mouseBuffer = [...ms, ...this.mouseBuffer]
      this.pendingRetry = { ks, ms }
      this.retryTimer = setTimeout(() => void this.flush(), 5000)
    }
  }

  // ── private helpers ────────────────────────────────────────────────────────

  private now(): number {
    return Date.now() - this.sessionStart
  }

  private scheduleFlushIfNeeded(): void {
    const total = this.keystrokeBuffer.length + this.mouseBuffer.length
    if (total >= BATCH_SIZE_THRESHOLD) {
      void this.flush()
    }
  }

  private scheduleTimer(): void {
    this.clearTimer()
    this.flushTimer = setInterval(() => void this.flush(), BATCH_TIME_MS)
  }

  private clearTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer)
      this.flushTimer = null
    }
    if (this.retryTimer) {
      clearTimeout(this.retryTimer)
      this.retryTimer = null
    }
  }

  private buildPayload() {
    const ks = this.keystrokeBuffer.filter((k) => k.up !== 0)
    const ms = this.mouseBuffer
    return this.buildPayloadFromBuffers(ks, ms)
  }

  private buildPayloadFromBuffers(ks: KeystrokeRow[], ms: MouseEventRow[]) {
    if (ks.length === 0 && ms.length === 0) return null

    // Always include both blocks so the backend receives a complete payload.
    // Empty data arrays are valid per the API contract.
    return {
      schema_version: 1 as const,
      client_time: new Date().toISOString(),
      keystrokes: {
        fields: ['client_id', 'cat', 'down', 'up', 'flight'] as const,
        data: ks.map((k) => [k.client_id, k.cat, k.down, k.up, k.flight] as const),
      },
      mouse: {
        fields: ['client_id', 'type', 't', 'x', 'y', 'btn', 'dx', 'dy'] as const,
        data: ms.map((m) => [m.client_id, m.type, m.t, m.x, m.y, m.btn, m.dx, m.dy] as const),
      },
    }
  }

  private getCsrfToken(): string {
    const match = document.cookie.match(/csrftoken=([^;]+)/)
    return match ? match[1] : ''
  }

  // Expose for debugging in thesis demos
  get bufferSize() {
    return { keystrokes: this.keystrokeBuffer.length, mouse: this.mouseBuffer.length }
  }

  get hasActiveSession() {
    return this.sessionToken !== null
  }

  // Allow EnrollmentPage to know pending retry state
  get pendingRetryState() {
    return this.pendingRetry
  }
}

export const collector = new BehaviorCollector()
