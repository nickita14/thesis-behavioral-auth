import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { deleteProfile, getProfileStatus } from '@/services/mlEngine'
import type { ProfileStatus } from '@/services/mlEngine'

export function SecurityProfilePage() {
  const [status, setStatus] = useState<ProfileStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    getProfileStatus()
      .then(setStatus)
      .catch(() => setError('Не удалось загрузить статус профиля.'))
      .finally(() => setLoading(false))
  }, [])

  const handleRetrain = async () => {
    if (!confirm('Удалить текущий профиль и начать обучение заново?')) return
    setDeleting(true)
    try {
      await deleteProfile()
      toast.success('Профиль удалён. Начните новую сессию сбора данных.')
      navigate('/enrollment')
    } catch {
      toast.error('Не удалось удалить профиль.')
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-lg py-12 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Поведенческий профиль</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Статус вашей поведенческой модели безопасности
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {status && (
        <>
          {/* Profile status card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {status.is_trained ? 'Профиль активен' : 'Профиль отсутствует'}
              </CardTitle>
              <CardDescription>
                {status.is_trained
                  ? 'Система использует вашу поведенческую модель при оценке транзакций.'
                  : 'Пройдите процедуру создания профиля, чтобы включить поведенческую защиту.'}
              </CardDescription>
            </CardHeader>

            {status.is_trained && status.profile ? (
              <CardContent className="space-y-3">
                <div className="rounded-lg bg-muted p-4 text-sm space-y-2">
                  <Row
                    label="Обучен"
                    value={new Date(status.profile.trained_at).toLocaleString('ru-RU')}
                  />
                  <Row
                    label="Образцов"
                    value={String(status.profile.n_training_samples)}
                  />
                  {status.profile.n_training_sessions != null && (
                    <Row
                      label="Сессий"
                      value={String(status.profile.n_training_sessions)}
                    />
                  )}
                  <Row
                    label="Схема признаков"
                    value={status.profile.feature_schema_version}
                  />
                  <Row
                    label="Детектор"
                    value={status.profile.detector_version}
                  />
                </div>
              </CardContent>
            ) : (
              <CardContent>
                <div className="rounded-lg bg-muted p-4 text-sm text-muted-foreground space-y-1">
                  <p>
                    Завершено сессий:{' '}
                    <span className="font-medium text-foreground">
                      {status.enrollment_sessions_completed} /{' '}
                      {status.enrollment_sessions_required}
                    </span>
                  </p>
                </div>
              </CardContent>
            )}
          </Card>

          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Действия</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {status.is_trained ? (
                <Button
                  variant="destructive"
                  className="w-full"
                  onClick={() => void handleRetrain()}
                  disabled={deleting}
                >
                  {deleting ? 'Удаление…' : 'Переобучить профиль'}
                </Button>
              ) : (
                <Link
                  to="/enrollment"
                  className="flex w-full items-center justify-center rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                  style={{ textDecoration: 'none', backgroundColor: 'var(--brand-primary)', color: '#ffffff' }}
                >
                  Начать создание профиля
                </Link>
              )}
            </CardContent>
          </Card>

          {/* Privacy notice */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Конфиденциальность</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-2">
              <p>
                Система хранит только <strong>временны́е характеристики</strong> нажатий клавиш:
                время удержания (dwell) и время между нажатиями (flight). Конкретные клавиши или
                введённый текст не сохраняются.
              </p>
              <p>
                Движения мыши записываются в виде агрегированных метрик — путь, скорость, количество
                кликов. Координаты не привязываются к содержимому страницы.
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}
