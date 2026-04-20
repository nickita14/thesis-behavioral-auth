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
import { PrivacyConsent } from '@/components/layout/PrivacyConsent'
import { login, register } from '@/services/auth'
import { collector } from '@/services/collector'
import { useAuthStore } from '@/store/auth'
import type { ApiError } from '@/types/api'

const schema = z
  .object({
    username: z
      .string()
      .min(3, 'Минимум 3 символа')
      .max(30, 'Максимум 30 символов')
      .regex(/^[a-zA-Z0-9_]+$/, 'Только буквы, цифры и _'),
    email: z.string().email('Некорректный email'),
    password: z.string().min(8, 'Минимум 8 символов'),
    passwordConfirm: z.string(),
  })
  .refine((d) => d.password === d.passwordConfirm, {
    message: 'Пароли не совпадают',
    path: ['passwordConfirm'],
  })

type FormValues = z.infer<typeof schema>

export function RegisterPage() {
  const [consented, setConsented] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)
  const navigate = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)

  const {
    register: field,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = async (values: FormValues) => {
    setServerError(null)
    try {
      await register({ username: values.username, email: values.email, password: values.password })
      const user = await login({ username: values.username, password: values.password })
      setUser(user)
      collector.start()
      navigate('/enrollment')
    } catch (err: unknown) {
      const data = (err as { response?: { data?: ApiError } }).response?.data
      if (data) {
        if (data.username) setError('username', { message: String(data.username) })
        if (data.email) setError('email', { message: String(data.email) })
        if (data.password) setError('password', { message: String(data.password) })
        if (data.detail) setServerError(data.detail)
      } else {
        setServerError('Произошла ошибка. Попробуйте ещё раз.')
      }
    }
  }

  return (
    <div className="flex justify-center py-12">
      <div className="w-full max-w-md">
        <PrivacyConsent onConsent={() => setConsented(true)} />

        {consented && (
          <Card>
            <CardHeader>
              <CardTitle>Регистрация</CardTitle>
              <CardDescription>Создайте аккаунт для начала работы</CardDescription>
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
                  <Input id="username" autoComplete="username" {...field('username')} />
                  {errors.username && (
                    <p className="text-sm text-destructive">{errors.username.message}</p>
                  )}
                </div>

                <div className="space-y-1">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" autoComplete="email" {...field('email')} />
                  {errors.email && (
                    <p className="text-sm text-destructive">{errors.email.message}</p>
                  )}
                </div>

                <div className="space-y-1">
                  <Label htmlFor="password">Пароль</Label>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="new-password"
                    {...field('password')}
                  />
                  {errors.password && (
                    <p className="text-sm text-destructive">{errors.password.message}</p>
                  )}
                </div>

                <div className="space-y-1">
                  <Label htmlFor="passwordConfirm">Подтвердите пароль</Label>
                  <Input
                    id="passwordConfirm"
                    type="password"
                    autoComplete="new-password"
                    {...field('passwordConfirm')}
                  />
                  {errors.passwordConfirm && (
                    <p className="text-sm text-destructive">{errors.passwordConfirm.message}</p>
                  )}
                </div>

                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? 'Регистрация...' : 'Зарегистрироваться'}
                </Button>
              </form>
              <p className="mt-4 text-center text-sm text-muted-foreground">
                Уже есть аккаунт?{' '}
                <Link to="/login" className="text-primary hover:underline">
                  Войти
                </Link>
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
