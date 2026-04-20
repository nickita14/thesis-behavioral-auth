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
      await collector.startSession(false)
      navigate('/dashboard')
    } catch (err: unknown) {
      const data = (err as { response?: { data?: ApiError } }).response?.data
      setServerError(data?.detail ?? 'Произошла ошибка. Попробуйте ещё раз.')
    }
  }

  return (
    <div className="flex justify-center py-12">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Вход</CardTitle>
          <CardDescription>Войдите в свой аккаунт</CardDescription>
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
    </div>
  )
}
