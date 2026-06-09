import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { collector } from '@/services/collector'
import { getProfileStatus, trainProfile } from '@/services/mlEngine'

// The CMU Keystroke Benchmark phrase — same distribution as training data
const TARGET_TEXT = '.tie5Roanl'
const TOTAL_REPS = 10
const TOTAL_SESSIONS = 5

type TrainingStatus = 'idle' | 'training' | 'success' | 'error'

export function EnrollmentPage() {
  const [current, setCurrent] = useState('')
  const [completed, setCompleted] = useState(0)
  const [started, setStarted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentSessionNumber, setCurrentSessionNumber] = useState(1)
  const [trainingStatus, setTrainingStatus] = useState<TrainingStatus>('idle')
  const [trainingSamples, setTrainingSamples] = useState<number | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  // Guards against React StrictMode's artificial double-invocation of effects,
  // which would otherwise create two enrollment sessions in development.
  const sessionStartedRef = useRef(false)

  useEffect(() => {
    if (sessionStartedRef.current) return
    sessionStartedRef.current = true

    const init = async () => {
      try {
        const status = await getProfileStatus()

        if (status.is_trained) {
          navigate('/security-profile', { replace: true })
          return
        }

        const sessionNum = Math.min(status.enrollment_sessions_completed + 1, TOTAL_SESSIONS)
        setCurrentSessionNumber(sessionNum)

        await collector.startSession(true)
        setStarted(true)
        inputRef.current?.focus()
      } catch {
        setError('Не удалось создать сессию. Проверьте подключение.')
      }
    }

    void init()
    // No cleanup — sessionStartedRef ensures init() runs exactly once,
    // so there is nothing to cancel on the StrictMode synthetic unmount.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleChange = async (value: string) => {
    setCurrent(value)

    if (value === TARGET_TEXT) {
      const next = completed + 1
      setCompleted(next)
      setCurrent('')

      if (next >= TOTAL_REPS) {
        await collector.endSession()

        // Check if this completed the required number of sessions
        const status = await getProfileStatus()
        if (status.ready_to_train) {
          await triggerTraining()
        } else {
          toast.success(`Сессия ${currentSessionNumber} из ${TOTAL_SESSIONS} завершена.`)
          navigate('/dashboard')
        }
      } else {
        inputRef.current?.focus()
      }
    }
  }

  const triggerTraining = async () => {
    setTrainingStatus('training')
    try {
      const result = await trainProfile()
      if (result.success && result.profile) {
        setTrainingStatus('success')
        setTrainingSamples(result.profile.n_training_samples)
      } else {
        setTrainingStatus('error')
        setError(result.error ?? 'Обучение не удалось.')
      }
    } catch {
      setTrainingStatus('error')
      setError('Ошибка при обучении модели. Попробуйте позже.')
    }
  }

  const progressPercent = Math.round((completed / TOTAL_REPS) * 100)
  const sessionProgressPercent = Math.round(((currentSessionNumber - 1) / TOTAL_SESSIONS) * 100)

  if (trainingStatus === 'training') {
    return (
      <div className="flex justify-center py-12">
        <Card className="w-full max-w-lg">
          <CardHeader>
            <CardTitle>Создание профиля безопасности…</CardTitle>
            <CardDescription>
              Система обрабатывает данные {TOTAL_SESSIONS} сессий и строит ваш поведенческий профиль.
              Это займёт несколько секунд.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (trainingStatus === 'success') {
    return (
      <div className="flex justify-center py-12">
        <Card className="w-full max-w-lg">
          <CardHeader>
            <CardTitle>Профиль безопасности создан</CardTitle>
            <CardDescription>
              Поведенческая модель обучена на {trainingSamples ?? '?'} образцах.
              Теперь система будет защищать ваши переводы с AI-верификацией личности.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg bg-muted p-4 text-sm text-muted-foreground space-y-1">
              <p>✓ Собрано сессий: {TOTAL_SESSIONS}</p>
              <p>✓ Обучающих образцов: {trainingSamples}</p>
              <p>✓ Алгоритм: Isolation Forest</p>
            </div>
            <Button className="w-full" onClick={() => navigate('/dashboard')}>
              Перейти в Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex justify-center py-12">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Обучение профиля безопасности</CardTitle>
          <CardDescription>
            Для защиты ваших переводов система создаёт индивидуальный поведенческий профиль.
            Введите контрольную фразу {TOTAL_REPS} раз — это займёт 1–2 минуты.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Session progress */}
          <div className="space-y-1">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>Сессия обучения</span>
              <span>
                {currentSessionNumber} из {TOTAL_SESSIONS}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full transition-all duration-300"
                style={{ width: `${sessionProgressPercent}%`, backgroundColor: 'var(--brand-accent)' }}
              />
            </div>
          </div>

          {/* Repetition progress */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>Повторений в текущей сессии</span>
              <span>
                {completed} из {TOTAL_REPS}
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
                role="progressbar"
                aria-valuenow={completed}
                aria-valuemin={0}
                aria-valuemax={TOTAL_REPS}
              />
            </div>
          </div>

          {/* Target phrase */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Введите контрольную фразу:</p>
            <p className="font-mono text-2xl tracking-widest text-center py-3 bg-muted rounded-lg select-none">
              {TARGET_TEXT}
            </p>
          </div>

          {/* Input field */}
          <div className="space-y-1">
            <Label htmlFor="enrollment-input">
              Повторение {Math.min(completed + 1, TOTAL_REPS)} из {TOTAL_REPS}
            </Label>
            <Input
              id="enrollment-input"
              ref={inputRef}
              value={current}
              onChange={(e) => void handleChange(e.target.value)}
              disabled={!started || completed >= TOTAL_REPS}
              placeholder={started ? 'Начните вводить...' : 'Подготовка...'}
              className="font-mono text-lg"
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck={false}
            />
            {current.length > 0 && !TARGET_TEXT.startsWith(current) && (
              <p className="text-sm text-destructive">Ошибка ввода — проверьте текст</p>
            )}
          </div>

          <Button
            variant="outline"
            className="w-full"
            onClick={() => {
              void collector.endSession().then(() => navigate('/dashboard'))
            }}
          >
            Завершить сейчас (профиль будет менее точным)
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
