import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/Logo'
import { BRAND } from '@/brand'
import { logout } from '@/services/auth'
import { collector } from '@/services/collector'
import { useAuthStore } from '@/store/auth'

interface Props {
  children: React.ReactNode
}

export function AppLayout({ children }: Props) {
  const { isAuthenticated, clearUser } = useAuthStore()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const isAuthPage = pathname === '/login' || pathname === '/register'
  const showAuthenticatedNav = isAuthenticated && !isAuthPage

  const handleLogout = async () => {
    if (collector.hasActiveSession) await collector.endSession()
    collector.stop()
    await logout()
    clearUser()
    navigate('/login')
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--background)' }}>
      <header
        style={{
          backgroundColor: BRAND.colors.primary,
          color: '#ffffff',
          boxShadow: '0 2px 8px rgba(0,0,0,0.18)',
        }}
      >
        <div className="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
          <Link to={isAuthenticated ? '/dashboard' : '/login'} style={{ textDecoration: 'none' }}>
            <Logo variant="white" size="md" />
          </Link>

          {showAuthenticatedNav && (
            <nav className="flex items-center gap-6">
              <NavLink to="/dashboard">Главная</NavLink>
              <NavLink to="/transactions/new">Переводы</NavLink>
              <NavLink to="/security-profile">Безопасность</NavLink>
            </nav>
          )}

          <div className="flex items-center gap-3">
            {showAuthenticatedNav && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => void handleLogout()}
                style={{
                  borderColor: 'rgba(255,255,255,0.5)',
                  color: '#ffffff',
                  backgroundColor: 'transparent',
                }}
              >
                Выйти
              </Button>
            )}
            {!isAuthenticated && (
              <nav className="flex items-center gap-4">
                {pathname !== '/login' && (
                  <NavLink to="/login">Войти</NavLink>
                )}
                {pathname !== '/register' && (
                  <NavLink to="/register">Регистрация</NavLink>
                )}
              </nav>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
    </div>
  )
}

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  const { pathname } = useLocation()
  const isActive = pathname === to || (to !== '/dashboard' && pathname.startsWith(to))
  return (
    <Link
      to={to}
      style={{
        color: isActive ? BRAND.colors.accent : 'rgba(255,255,255,0.85)',
        textDecoration: 'none',
        fontSize: 14,
        fontWeight: isActive ? 600 : 400,
        borderBottom: isActive ? `2px solid ${BRAND.colors.accent}` : '2px solid transparent',
        paddingBottom: 2,
        transition: 'color 0.15s',
      }}
    >
      {children}
    </Link>
  )
}
