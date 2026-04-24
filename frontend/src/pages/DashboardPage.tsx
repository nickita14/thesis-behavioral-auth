import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { ShieldCheck, MousePointer2, Keyboard, Link2, Activity } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { getDashboardData } from '@/services/dashboard'
import { useAuthStore } from '@/store/auth'
import type { DashboardData } from '@/types/api'

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatDuration(durationMs: number | null): string {
  if (durationMs === null) return 'активна'
  const seconds = Math.max(Math.round(durationMs / 1000), 0)
  if (seconds < 60) return `${seconds} сек`
  return `${Math.floor(seconds / 60)} мин ${seconds % 60} сек`
}

function shortUrl(url: string): string {
  return url.length > 52 ? `${url.slice(0, 49)}...` : url
}

export function DashboardPage() {
  const user = useAuthStore((state) => state.user)
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true

    async function loadDashboard() {
      try {
        const response = await getDashboardData()
        if (active) setData(response)
      } catch {
        if (active) setError('Не удалось загрузить demo telemetry. Попробуйте обновить страницу.')
      } finally {
        if (active) setIsLoading(false)
      }
    }

    void loadDashboard()

    return () => {
      active = false
    }
  }, [])

  if (isLoading) {
    return (
      <div className="py-8">
        <Card>
          <CardHeader>
            <CardTitle>Загрузка security dashboard...</CardTitle>
            <CardDescription>Получаем последние behavior sessions и phishing checks.</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="py-8">
        <Alert variant="destructive">
          <AlertTitle>Dashboard недоступен</AlertTitle>
          <AlertDescription>{error ?? 'Пустой ответ от backend.'}</AlertDescription>
        </Alert>
      </div>
    )
  }

  const totals = data.behavior.totals
  const phishing = data.phishing.totals

  return (
    <div className="space-y-6 py-8">
      <section className="rounded-3xl border bg-gradient-to-br from-muted/80 via-background to-background p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
              Transaction authentication demo
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">
              Security dashboard для {user?.username}
            </h1>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              Backend уже принимает поведенческие события и сохраняет phishing audit log.
              Здесь показаны только метаданные: raw key values не отображаются и не хранятся.
            </p>
          </div>
          <div className="rounded-full border bg-card px-4 py-2 text-sm">
            Статус: <span className="font-medium">{data.security_status.level}</span>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <StatCard title="Sessions" value={totals.sessions} icon={<Activity className="size-5" />} />
        <StatCard title="Keystrokes" value={totals.keystrokes} icon={<Keyboard className="size-5" />} />
        <StatCard title="Mouse events" value={totals.mouse} icon={<MousePointer2 className="size-5" />} />
        <StatCard title="Phishing checks" value={phishing.checks} icon={<Link2 className="size-5" />} />
      </section>

      <Alert>
        <ShieldCheck className="size-4" />
        <AlertTitle>Текущий security status</AlertTitle>
        <AlertDescription>
          {data.security_status.message} {data.security_status.privacy_note}
        </AlertDescription>
      </Alert>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Последние behavior sessions</CardTitle>
            <CardDescription>
              Сессии пользователя с количеством timing metadata для клавиатуры и мыши.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.behavior.sessions.length === 0 ? (
              <EmptyState text="Сессии ещё не записаны. После логина collector создаст первую session." />
            ) : (
              <div className="space-y-3">
                {data.behavior.sessions.map((session) => (
                  <div key={session.id} className="rounded-xl border bg-muted/30 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium">
                          {session.is_enrollment ? 'Enrollment' : 'Login/transaction'} session
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(session.started_at)} · {formatDuration(session.duration_ms)}
                        </p>
                      </div>
                      <span className="rounded-full bg-card px-2.5 py-1 text-xs ring-1 ring-border">
                        {session.ended_at ? 'closed' : 'active'}
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                      <Metric label="Keystrokes" value={session.keystroke_count} />
                      <Metric label="Mouse" value={session.mouse_count} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Последние phishing checks</CardTitle>
            <CardDescription>
              URL audit log: результат классификации и confidence модели.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.phishing.checks.length === 0 ? (
              <EmptyState text="Проверок URL пока нет. Они появятся после вызова phishing API." />
            ) : (
              <div className="space-y-3">
                {data.phishing.checks.map((check) => (
                  <div key={check.id} className="rounded-xl border bg-muted/30 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium" title={check.url}>
                          {shortUrl(check.url)}
                        </p>
                        <p className="text-xs text-muted-foreground">{formatDate(check.created_at)}</p>
                      </div>
                      <span className="rounded-full bg-card px-2.5 py-1 text-xs ring-1 ring-border">
                        {check.is_phishing_predicted ? 'phishing' : 'clean'}
                      </span>
                    </div>
                    <Metric label="Confidence" value={`${Math.round(check.confidence * 100)}%`} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  )
}

function StatCard({
  title,
  value,
  icon,
}: {
  title: string
  value: number
  icon: ReactNode
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm text-muted-foreground">{title}</CardTitle>
        <div className="text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  )
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="mt-3 rounded-lg bg-card px-3 py-2 ring-1 ring-border">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  )
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">{text}</div>
}
