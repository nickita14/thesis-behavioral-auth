import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Logo } from '@/components/Logo'
import { BRAND } from '@/brand'
import { login } from '@/services/auth'
import { collector } from '@/services/collector'
import { useAuthStore } from '@/store/auth'
import type { ApiError } from '@/types/api'

const schema = z.object({
  username: z.string().min(1, 'Введите имя пользователя'),
  password: z.string().min(1, 'Введите пароль'),
})

type FormValues = z.infer<typeof schema>

export function LoginPage() {
  const [serverError, setServerError] = useState<string | null>(null)
  const navigate = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = async (values: FormValues) => {
    setServerError(null)
    try {
      const user = await login(values)
      setUser(user)
      collector.start()
      try {
        await collector.startSession(false)
      } catch {
        // Behavior collection must not turn a successful auth/login into a failed login.
      }
      navigate('/dashboard')
    } catch (err: unknown) {
      const data = (err as { response?: { data?: ApiError } }).response?.data
      setServerError(data?.detail ?? 'Произошла ошибка. Попробуйте ещё раз.')
    }
  }

  return (
    <div className="flex flex-col items-center justify-center py-12">
      {/* Logo + tagline above card */}
      <div className="mb-8 flex flex-col items-center gap-3">
        <Logo variant="full" size="lg" />
        <p style={{ color: BRAND.colors.textSecondary, fontSize: 14, textAlign: 'center' }}>
          {BRAND.tagline}
        </p>
      </div>

      <Card className="w-full max-w-md shadow-md">
        <CardHeader>
          <CardTitle>Вход в личный кабинет</CardTitle>
          <CardDescription>Введите данные вашей учётной записи</CardDescription>
        </CardHeader>
        <CardContent>
          {serverError && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{serverError}</AlertDescription>
            </Alert>
          )}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div className="space-y-1">
              <Label htmlFor="username">Имя пользователя</Label>
              <Input id="username" autoComplete="username" {...register('username')} />
              {errors.username && (
                <p className="text-sm text-destructive">{errors.username.message}</p>
              )}
            </div>

            <div className="space-y-1">
              <Label htmlFor="password">Пароль</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register('password')}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Вход...' : 'Войти'}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Нет аккаунта?{' '}
            <Link to="/register" className="text-primary hover:underline">
              Зарегистрироваться
            </Link>
          </p>
        </CardContent>
      </Card>

      <p className="mt-6 text-xs" style={{ color: BRAND.colors.textSecondary }}>
        🔒 Защищено AI-аналитикой поведения · Sigur Bank © 2026
      </p>
    </div>
  )
}
