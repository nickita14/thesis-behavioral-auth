import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ShieldCheck, ArrowUpRight, ArrowDownLeft, Activity, Keyboard, MousePointer2, Link2 } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { BRAND } from '@/brand'
import { getDashboardData } from '@/services/dashboard'
import { getProfileStatus } from '@/services/mlEngine'
import { useAuthStore } from '@/store/auth'
import type { DashboardData } from '@/types/api'
import type { ProfileStatus } from '@/services/mlEngine'

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatBalance(amount: number): string {
  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
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

const STATUS_COLORS: Record<string, string> = {
  allowed: BRAND.colors.success,
  challenge: BRAND.colors.warning,
  denied: BRAND.colors.danger,
}

const STATUS_LABELS: Record<string, string> = {
  allowed: 'Выполнен',
  challenge: 'Проверка',
  denied: 'Отклонён',
}

export function DashboardPage() {
  const user = useAuthStore((state) => state.user)
  const [data, setData] = useState<DashboardData | null>(null)
  const [profileStatus, setProfileStatus] = useState<ProfileStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const [dashRes, profileRes] = await Promise.all([
          getDashboardData(),
          getProfileStatus().catch(() => null),
        ])
        if (active) {
          setData(dashRes)
          setProfileStatus(profileRes)
        }
      } catch {
        if (active) setError('Не удалось загрузить данные. Попробуйте обновить страницу.')
      } finally {
        if (active) setIsLoading(false)
      }
    }
    void load()
    return () => { active = false }
  }, [])

  if (isLoading) {
    return (
      <div className="py-8">
        <Card>
          <CardHeader>
            <CardTitle>Загрузка личного кабинета...</CardTitle>
            <CardDescription>Получаем данные вашего счёта и профиля безопасности.</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="py-8">
        <Alert variant="destructive">
          <AlertTitle>Ошибка загрузки</AlertTitle>
          <AlertDescription>{error ?? 'Пустой ответ от сервера.'}</AlertDescription>
        </Alert>
      </div>
    )
  }

  const totals = data.behavior.totals
  const phishing = data.phishing.totals

  return (
    <div className="space-y-6 py-4">
      {/* ── Account balance + greeting ── */}
      <section
        className="rounded-2xl p-6"
        style={{ backgroundColor: BRAND.colors.primary, color: '#fff' }}
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm opacity-70">{BRAND.mockAccount.accountType}</p>
            <p className="text-xs opacity-50 mt-0.5">{BRAND.mockAccount.accountNumber}</p>
            <p className="mt-3 text-4xl font-bold tracking-tight">
              {formatBalance(BRAND.mockAccount.balance)}{' '}
              <span className="text-2xl font-semibold opacity-80">{BRAND.mockAccount.currency}</span>
            </p>
            <p className="mt-1 text-sm opacity-70">Доступный баланс · {user?.username}</p>
          </div>
          <Link
            to="/transactions/new"
            style={{
              backgroundColor: BRAND.colors.accent,
              color: BRAND.colors.primaryDark,
              fontWeight: 600,
              fontSize: 14,
              padding: '8px 20px',
              borderRadius: 8,
              textDecoration: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            Перевести деньги →
          </Link>
        </div>
      </section>

      {/* ── Security profile status card ── */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
              <ShieldCheck className="size-4" /> Профиль безопасности
            </CardTitle>
          </CardHeader>
          <CardContent>
            {profileStatus?.is_trained ? (
              <div>
                <p className="text-lg font-semibold" style={{ color: BRAND.colors.success }}>
                  Активен
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Поведенческая модель обучена · {profileStatus.profile?.n_training_samples ?? '?'} образцов
                </p>
                <Link
                  to="/security-profile"
                  className="mt-3 flex w-full items-center justify-center rounded-lg border border-border bg-background px-3 py-1.5 text-sm font-medium hover:bg-muted transition-colors"
                  style={{ textDecoration: 'none', color: 'inherit' }}
                >
                  Управление
                </Link>
              </div>
            ) : (
              <div>
                <p className="text-lg font-semibold" style={{ color: BRAND.colors.warning }}>
                  Не настроен
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Завершено сессий: {profileStatus?.enrollment_sessions_completed ?? 0} /{' '}
                  {profileStatus?.enrollment_sessions_required ?? 5}
                </p>
                <Link
                  to="/enrollment"
                  className="mt-3 flex w-full items-center justify-center rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
                  style={{
                    textDecoration: 'none',
                    backgroundColor: BRAND.colors.primary,
                    color: '#ffffff',
                  }}
                >
                  Пройти обучение
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="md:col-span-2 grid grid-cols-2 gap-4">
          <StatCard title="Поведенческих сессий" value={totals.sessions} icon={<Activity className="size-4" />} />
          <StatCard title="Нажатий клавиш" value={totals.keystrokes} icon={<Keyboard className="size-4" />} />
          <StatCard title="Событий мыши" value={totals.mouse} icon={<MousePointer2 className="size-4" />} />
          <StatCard title="Проверок URL" value={phishing.checks} icon={<Link2 className="size-4" />} />
        </div>
      </div>

      {/* ── Mock transaction history ── */}
      <Card>
        <CardHeader>
          <CardTitle>История операций</CardTitle>
          <CardDescription>Последние транзакции по вашему счёту</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="pb-2 text-left font-medium">Дата</th>
                  <th className="pb-2 text-left font-medium">Получатель / Описание</th>
                  <th className="pb-2 text-right font-medium">Сумма</th>
                  <th className="pb-2 text-right font-medium">Статус</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {BRAND.mockHistory.map((tx) => (
                  <tr key={tx.id}>
                    <td className="py-3 text-muted-foreground">{tx.date}</td>
                    <td className="py-3">
                      <p className="font-medium">{tx.recipient}</p>
                      <p className="text-xs text-muted-foreground">{tx.description}</p>
                    </td>
                    <td className="py-3 text-right font-semibold">
                      <span style={{ color: tx.amount < 0 ? BRAND.colors.text : BRAND.colors.success }}>
                        {tx.amount > 0 ? '+' : ''}
                        {formatBalance(tx.amount)} MDL
                      </span>
                      <div className="flex justify-end mt-0.5">
                        {tx.amount < 0
                          ? <ArrowUpRight className="size-3 opacity-40" />
                          : <ArrowDownLeft className="size-3" style={{ color: BRAND.colors.success }} />
                        }
                      </div>
                    </td>
                    <td className="py-3 text-right">
                      <span
                        className="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
                        style={{
                          backgroundColor: `${STATUS_COLORS[tx.status]}18`,
                          color: STATUS_COLORS[tx.status],
                        }}
                      >
                        {STATUS_LABELS[tx.status]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ── Telemetry (behavior sessions + phishing log) ── */}
      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Мониторинг поведения</CardTitle>
            <CardDescription>
              Метаданные поведенческих сессий. Содержимое клавиш не записывается.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.behavior.sessions.length === 0 ? (
              <EmptyState text="Сессии ещё не записаны. Данные появятся после первого входа в систему." />
            ) : (
              <div className="space-y-3">
                {data.behavior.sessions.map((session) => (
                  <div key={session.id} className="rounded-xl border bg-muted/30 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium text-sm">
                          {session.is_enrollment ? 'Сессия обучения' : 'Рабочая сессия'}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(session.started_at)} · {formatDuration(session.duration_ms)}
                        </p>
                      </div>
                      <span className="rounded-full bg-card px-2.5 py-1 text-xs ring-1 ring-border">
                        {session.ended_at ? 'завершена' : 'активна'}
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                      <Metric label="Нажатий" value={session.keystroke_count} />
                      <Metric label="Событий мыши" value={session.mouse_count} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Проверки безопасности URL</CardTitle>
            <CardDescription>
              Лог phishing-анализа для каждой операции перевода.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.phishing.checks.length === 0 ? (
              <EmptyState text="Проверок URL пока нет. Они появятся при выполнении переводов." />
            ) : (
              <div className="space-y-3">
                {data.phishing.checks.map((check) => (
                  <div key={check.id} className="rounded-xl border bg-muted/30 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-sm" title={check.url}>
                          {shortUrl(check.url)}
                        </p>
                        <p className="text-xs text-muted-foreground">{formatDate(check.created_at)}</p>
                      </div>
                      <span
                        className="rounded-full px-2.5 py-1 text-xs shrink-0"
                        style={{
                          color: check.is_phishing_predicted ? BRAND.colors.danger : BRAND.colors.success,
                          backgroundColor: check.is_phishing_predicted
                            ? `${BRAND.colors.danger}18`
                            : `${BRAND.colors.success}18`,
                        }}
                      >
                        {check.is_phishing_predicted ? 'фишинг' : 'безопасен'}
                      </span>
                    </div>
                    <Metric label="Уверенность" value={`${Math.round(check.confidence * 100)}%`} />
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

function StatCard({ title, value, icon }: { title: string; value: number; icon: ReactNode }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-1">
        <CardTitle className="text-xs text-muted-foreground">{title}</CardTitle>
        <div className="text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  )
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="mt-2 rounded-lg bg-card px-3 py-2 ring-1 ring-border">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  )
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">{text}</div>
}
