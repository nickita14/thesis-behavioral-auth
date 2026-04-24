import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { logout } from '@/services/auth'
import { collector } from '@/services/collector'
import { useAuthStore } from '@/store/auth'

interface Props {
  children: React.ReactNode
}

export function AppLayout({ children }: Props) {
  const { isAuthenticated, clearUser } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = async () => {
    if (collector.hasActiveSession) await collector.endSession()
    collector.stop()
    await logout()
    clearUser()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            Behavioral Auth Demo
          </Link>
          {isAuthenticated && (
            <nav className="flex items-center gap-4">
              <Link
                to="/dashboard"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Dashboard
              </Link>
              <Link
                to="/transactions/new"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                New transaction
              </Link>
              <Button variant="outline" size="sm" onClick={() => void handleLogout()}>
                Logout
              </Button>
            </nav>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
    </div>
  )
}
