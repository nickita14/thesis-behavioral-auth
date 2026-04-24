import { useState } from 'react'
import type { FormEvent } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { collector } from '@/services/collector'
import { createTransactionAttempt } from '@/services/transactions'
import type { TransactionAttemptResult } from '@/types/api'

const DECISION_LABELS = {
  ALLOW: 'Разрешить',
  CHALLENGE: 'Дополнительная проверка',
  DENY: 'Отклонить',
  PENDING: 'Ожидает проверки',
}

export function TransactionPage() {
  const [amount, setAmount] = useState('150.00')
  const [currency, setCurrency] = useState('MDL')
  const [recipient, setRecipient] = useState('Test Recipient')
  const [targetUrl, setTargetUrl] = useState('https://example.com/payment')
  const [result, setResult] = useState<TransactionAttemptResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setResult(null)
    setIsSubmitting(true)

    try {
      const response = await createTransactionAttempt({
        amount,
        currency,
        recipient,
        target_url: targetUrl,
        behavior_session_id: collector.activeSessionId ?? undefined,
      })
      setResult(response)
    } catch {
      setError('Не удалось создать transaction attempt. Проверьте данные и повторите.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="grid gap-6 py-8 lg:grid-cols-[1fr_0.9fr]">
      <Card>
        <CardHeader>
          <CardTitle>Transaction authentication</CardTitle>
          <CardDescription>
            Создаёт TransactionAttempt и RiskAssessment без ML risk engine. Behavior session
            прикрепляется автоматически, если collector активен.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="amount">Amount</Label>
                <Input
                  id="amount"
                  inputMode="decimal"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="currency">Currency</Label>
                <Input
                  id="currency"
                  value={currency}
                  maxLength={3}
                  onChange={(event) => setCurrency(event.target.value.toUpperCase())}
                  required
                />
              </div>
            </div>

            <div className="space-y-1">
              <Label htmlFor="recipient">Recipient</Label>
              <Input
                id="recipient"
                value={recipient}
                onChange={(event) => setRecipient(event.target.value)}
                required
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="target-url">Target URL</Label>
              <Input
                id="target-url"
                type="url"
                value={targetUrl}
                onChange={(event) => setTargetUrl(event.target.value)}
                placeholder="https://example.com/payment"
              />
              <p className="text-xs text-muted-foreground">
                Если URL указан, backend выполнит phishing check. При ошибке проверки решение
                безопасно переходит в CHALLENGE.
              </p>
            </div>

            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Проверка...' : 'Создать transaction attempt'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Alert>
          <AlertTitle>Skeleton decision logic</AlertTitle>
          <AlertDescription>
            phishing → DENY, suspicious URL → CHALLENGE, anomalous behavior → CHALLENGE,
            high amount + suspicious behavior → CHALLENGE. Ошибки анализа обрабатываются
            безопасно и не раскрывают raw key values.
          </AlertDescription>
        </Alert>

        {error && (
          <Alert variant="destructive">
            <AlertTitle>Ошибка</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {result && (
          <Card>
            <CardHeader>
              <CardTitle>RiskAssessment result</CardTitle>
              <CardDescription>Attempt ID: {result.id}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-2xl border bg-muted/40 p-4">
                <p className="text-sm text-muted-foreground">Decision</p>
                <p className="text-3xl font-semibold">{DECISION_LABELS[result.decision]}</p>
                <p className="mt-1 text-sm text-muted-foreground">{result.explanation}</p>
              </div>

              <div className="grid gap-3 text-sm sm:grid-cols-2">
                <Metric label="Amount" value={`${result.amount} ${result.currency}`} />
                <Metric label="Risk score" value={result.risk_score ?? 'n/a'} />
                <Metric label="Behavior session" value={result.behavior_session_id ? 'attached' : 'none'} />
                <Metric label="Phishing decision" value={result.phishing?.decision ?? 'not checked'} />
                <Metric label="Behavior decision" value={result.behavior.decision} />
              </div>

              {result.phishing && (
                <p className="text-sm text-muted-foreground">
                  Probability phishing:{' '}
                  {result.phishing.probability_phishing === null
                    ? 'n/a'
                    : `${Math.round(result.phishing.probability_phishing * 100)}%`}
                </p>
              )}
              <p className="text-sm text-muted-foreground">
                Behavior anomaly score:{' '}
                {result.behavior.anomaly_score === null
                  ? 'n/a'
                  : result.behavior.anomaly_score.toFixed(3)}
              </p>
              {result.reasons.length > 0 && (
                <div className="rounded-xl border bg-muted/30 p-3">
                  <p className="text-sm font-medium">Decision reasons</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                    {result.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        )}
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
