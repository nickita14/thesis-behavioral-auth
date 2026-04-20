import { useState } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

const CONSENT_KEY = 'behavioral_auth_consent'

interface Props {
  onConsent: () => void
}

export function PrivacyConsent({ onConsent }: Props) {
  const [declined, setDeclined] = useState(false)

  // If already consented in a previous visit, skip the banner
  if (localStorage.getItem(CONSENT_KEY) === 'granted') {
    onConsent()
    return null
  }

  if (declined) {
    return (
      <Alert variant="destructive" className="mb-6">
        <AlertTitle>Регистрация недоступна</AlertTitle>
        <AlertDescription>
          Для работы системы требуется сбор поведенческих данных. Без согласия регистрация невозможна.
        </AlertDescription>
      </Alert>
    )
  }

  const handleAccept = () => {
    localStorage.setItem(CONSENT_KEY, 'granted')
    onConsent()
  }

  return (
    <Alert className="mb-6 border-primary/30 bg-primary/5">
      <AlertTitle className="text-base font-semibold mb-2">Уведомление о сборе данных</AlertTitle>
      <AlertDescription className="space-y-4">
        <p className="text-sm leading-relaxed">
          Это демонстрационная система для магистерской диссертации USM. Для аутентификации система
          собирает поведенческие данные: ритм нажатий клавиш (без сохранения самих клавиш —
          только категории), движения и клики мыши. Данные хранятся локально на этом сервере, не
          передаются третьим лицам и используются исключительно для построения вашего поведенческого
          профиля.
        </p>
        <p className="text-sm font-medium">Согласны?</p>
        <div className="flex gap-3">
          <Button size="sm" onClick={handleAccept}>
            Согласен
          </Button>
          <Button size="sm" variant="outline" onClick={() => setDeclined(true)}>
            Не согласен
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  )
}
