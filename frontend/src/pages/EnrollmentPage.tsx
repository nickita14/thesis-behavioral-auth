import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { collector } from '@/services/collector'

// The CMU Keystroke Benchmark phrase — same distribution as training data
const TARGET_TEXT = '.tie5Roanl'
const TOTAL_REPS = 5

export function EnrollmentPage() {
  const [current, setCurrent] = useState('')
  const [completed, setCompleted] = useState(0)
  const [started, setStarted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    let active = true

    const init = async () => {
      try {
        await collector.startSession(true)
        if (active) {
          setStarted(true)
          inputRef.current?.focus()
        }
      } catch {
        if (active) setError('Не удалось создать сессию. Проверьте подключение.')
      }
    }

    void init()

    return () => {
      active = false
      // End session on unmount only if enrollment not completed
      if (collector.hasActiveSession) {
        void collector.endSession()
      }
    }
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
        toast.success('Профиль создан! Теперь система знает ваш стиль набора.')
        navigate('/dashboard')
      } else {
        inputRef.current?.focus()
      }
    }
  }

  const progressPercent = Math.round((completed / TOTAL_REPS) * 100)

  return (
    <div className="flex justify-center py-12">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Создание поведенческого профиля</CardTitle>
          <CardDescription>
            Чтобы система научилась распознавать вашу манеру набора, введите следующий текст{' '}
            {TOTAL_REPS} раз. Это займёт 1–2 минуты.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Progress */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>Прогресс</span>
              <span>
                {completed} / {TOTAL_REPS}
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
            <p className="text-sm text-muted-foreground">Текст для ввода:</p>
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
            Пропустить (данных будет меньше)
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
