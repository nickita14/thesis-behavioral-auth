import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { BRAND } from '@/brand'
import { translateDecision, translateReason, translateReasons } from '@/i18n/reasons'
import { collector } from '@/services/collector'
import { createTransactionAttempt } from '@/services/transactions'
import type { TransactionAttemptResult } from '@/types/api'

const CHALLENGE_TEXT = '.tie5Roanl'

const DECISION_STYLES: Record<string, { label: string; color: string; bg: string }> = {
  ALLOW:     { label: 'Операция одобрена',               color: BRAND.colors.success, bg: `${BRAND.colors.success}12` },
  CHALLENGE: { label: 'Требуется дополнительная проверка', color: BRAND.colors.warning, bg: `${BRAND.colors.warning}12` },
  DENY:      { label: 'Операция отклонена',               color: BRAND.colors.danger,  bg: `${BRAND.colors.danger}12`  },
  PENDING:   { label: 'Ожидает проверки',                 color: BRAND.colors.textSecondary, bg: '#88888812' },
}

interface FormData {
  amount: string
  currency: string
  recipient: string
  targetUrl: string
}

export function TransactionPage() {
  const [step, setStep] = useState<'form' | 'challenge' | 'result'>('form')
  const [formData, setFormData] = useState<FormData>({
    amount: '150.00',
    currency: 'MDL',
    recipient: 'Test Recipient',
    targetUrl: 'https://example.com/payment',
  })
  const [challengeInput, setChallengeInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState<TransactionAttemptResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const challengeStartedRef = useRef(false)
  const challengeInputRef = useRef<HTMLInputElement>(null)

  // Close any pre-existing behavior session (e.g. started on login page).
  useEffect(() => {
    void collector.endSession()
  }, [])

  // Open a fresh behavior session when the challenge step begins.
  useEffect(() => {
    if (step !== 'challenge') return
    if (challengeStartedRef.current) return
    challengeStartedRef.current = true

    void collector.startSession(false)
    setTimeout(() => challengeInputRef.current?.focus(), 50)
  }, [step])

  const handleFormSubmit = (e: { preventDefault(): void }) => {
    e.preventDefault()
    setStep('challenge')
  }

  const submitTransaction = async () => {
    if (isSubmitting) return
    setIsSubmitting(true)

    // Capture session id before ending the session.
    const sessionId = collector.activeSessionId
    await collector.endSession()

    try {
      const response = await createTransactionAttempt({
        amount: formData.amount,
        currency: formData.currency,
        recipient: formData.recipient,
        target_url: formData.targetUrl,
        behavior_session_id: sessionId ?? undefined,
      })
      setResult(response)
    } catch {
      setError('Не удалось выполнить перевод. Проверьте данные и повторите.')
    } finally {
      setIsSubmitting(false)
      setStep('result')
    }
  }

  const handleChallengeChange = (value: string) => {
    setChallengeInput(value)
    if (value === CHALLENGE_TEXT) {
      void submitTransaction()
    }
  }

  const handleNewTransaction = () => {
    setChallengeInput('')
    setResult(null)
    setError(null)
    setStep('form')
    challengeStartedRef.current = false
  }

  if (step === 'form') {
    return (
      <div className="mx-auto max-w-lg py-8">
        <Card>
          <CardHeader>
            <CardTitle>Новый перевод</CardTitle>
            <CardDescription>
              Заполните реквизиты перевода. На следующем шаге система верифицирует вашу личность.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleFormSubmit}>
              {/* Read-only "from" account */}
              <div className="space-y-1">
                <Label>Со счёта</Label>
                <div
                  className="rounded-lg border px-3 py-2 text-sm"
                  style={{ backgroundColor: 'var(--muted)', color: 'var(--muted-foreground)' }}
                >
                  <span className="font-mono">{BRAND.mockAccount.accountNumber}</span>
                  <span className="ml-2 text-xs">
                    · {BRAND.mockAccount.accountType}
                  </span>
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="recipient">Счёт получателя или IBAN</Label>
                <Input
                  id="recipient"
                  value={formData.recipient}
                  onChange={(e) => setFormData((d) => ({ ...d, recipient: e.target.value }))}
                  placeholder="Иванов И.И. или IBAN счёта"
                  required
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1">
                  <Label htmlFor="amount">Сумма перевода</Label>
                  <Input
                    id="amount"
                    inputMode="decimal"
                    value={formData.amount}
                    onChange={(e) => setFormData((d) => ({ ...d, amount: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="currency">Валюта</Label>
                  <Input
                    id="currency"
                    value={formData.currency}
                    maxLength={3}
                    onChange={(e) =>
                      setFormData((d) => ({ ...d, currency: e.target.value.toUpperCase() }))
                    }
                    required
                  />
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="target-url">URL ресурса (для проверки безопасности)</Label>
                <Input
                  id="target-url"
                  type="url"
                  value={formData.targetUrl}
                  onChange={(e) => setFormData((d) => ({ ...d, targetUrl: e.target.value }))}
                  placeholder="https://example.com/payment"
                />
                <p className="text-xs text-muted-foreground">
                  AI-система выполнит phishing-проверку указанного адреса.
                </p>
              </div>

              <Button type="submit" className="w-full">
                Перейти к подтверждению →
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (step === 'challenge') {
    const charCount = challengeInput.length
    const isWrong = challengeInput.length > 0 && !CHALLENGE_TEXT.startsWith(challengeInput)

    return (
      <div className="mx-auto max-w-lg py-8">
        <Card>
          <CardHeader>
            <CardTitle>Подтверждение операции</CardTitle>
            <CardDescription>
              Введите контрольную фразу для подтверждения перевода.
              Система проверит ваш поведенческий профиль.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div
              className="rounded-xl p-4 text-center"
              style={{ backgroundColor: `${BRAND.colors.primary}10`, border: `1px solid ${BRAND.colors.primary}30` }}
            >
              <p className="text-xs text-muted-foreground mb-2">Контрольная фраза</p>
              <p className="font-mono text-2xl tracking-widest select-none" style={{ color: BRAND.colors.primary }}>
                {CHALLENGE_TEXT}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>Введено символов</span>
                <span>{charCount} / {CHALLENGE_TEXT.length}</span>
              </div>
              <Input
                ref={challengeInputRef}
                value={challengeInput}
                onChange={(e) => handleChallengeChange(e.target.value)}
                disabled={isSubmitting}
                placeholder="Начните вводить..."
                className="font-mono text-lg"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
              />
              {isWrong && (
                <p className="text-sm text-destructive">Ошибка — проверьте текст и начните заново</p>
              )}
            </div>

            <p className="text-xs text-muted-foreground text-center">
              Перевод будет подтверждён автоматически после ввода полной фразы
            </p>

            {isSubmitting && (
              <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                Обработка транзакции…
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  // step === 'result'
  const decisionStyle = result ? (DECISION_STYLES[result.decision] ?? DECISION_STYLES['PENDING']) : null

  return (
    <div className="mx-auto max-w-lg py-8 space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Ошибка</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && decisionStyle && (
        <Card>
          <CardHeader>
            <div
              className="rounded-xl px-4 py-3 mb-2"
              style={{ backgroundColor: decisionStyle.bg, border: `1px solid ${decisionStyle.color}30` }}
            >
              <p className="text-2xl font-bold" style={{ color: decisionStyle.color }}>
                {decisionStyle.label}
              </p>
              <p className="text-sm mt-1" style={{ color: decisionStyle.color, opacity: 0.85 }}>
                {translateReason(result.explanation)}
              </p>
            </div>
            <CardDescription>ID транзакции: {result.id}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 text-sm sm:grid-cols-2">
              <Metric label="Сумма" value={`${result.amount} ${result.currency}`} />
              <Metric label="Итоговый риск" value={result.risk_score ?? 'n/a'} />
              <Metric
                label="Phishing-проверка"
                value={result.phishing?.decision
                  ? translateDecision(result.phishing.decision)
                  : 'не проверялся'}
              />
              <Metric label="Поведенческий анализ" value={translateDecision(result.behavior.decision)} />
              <Metric
                label="Аномальность"
                value={
                  result.behavior.anomaly_score === null
                    ? 'n/a'
                    : result.behavior.anomaly_score.toFixed(3)
                }
              />
              <Metric
                label="Поведенческая сессия"
                value={result.behavior_session_id ? 'прикреплена' : 'нет'}
              />
            </div>

            {result.reasons.length > 0 && (
              <div className="rounded-xl border bg-muted/30 p-3">
                <p className="text-sm font-medium mb-2">Причины решения</p>
                <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                  {translateReasons(result.reasons).map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <div className="flex gap-3">
        <Button variant="outline" className="flex-1" onClick={handleNewTransaction}>
          Новый перевод
        </Button>
        <Link
          to="/dashboard"
          className="flex-1 flex items-center justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium hover:bg-muted transition-colors"
          style={{ textDecoration: 'none', color: 'inherit' }}
        >
          На главную
        </Link>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl bg-card px-3 py-2 ring-1 ring-border">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  )
}
