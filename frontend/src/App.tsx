import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppLayout } from '@/components/layout/AppLayout'
import { PrivateRoute } from '@/components/PrivateRoute'
import { DashboardPage } from '@/pages/DashboardPage'
import { EnrollmentPage } from '@/pages/EnrollmentPage'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { TransactionPage } from '@/pages/TransactionPage'
import { ensureCsrf, getCurrentUser } from '@/services/auth'
import { collector } from '@/services/collector'
import { useAuthStore } from '@/store/auth'

const queryClient = new QueryClient()

function AppRoutes() {
  const { isAuthenticated, setUser } = useAuthStore()

  useEffect(() => {
    const init = async () => {
      await ensureCsrf()
      const currentUser = await getCurrentUser()
      if (currentUser) {
        setUser(currentUser)
        collector.start()
      }
    }
    void init()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <AppLayout>
      <Routes>
        <Route
          path="/"
          element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />}
        />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/enrollment"
          element={
            <PrivateRoute>
              <EnrollmentPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <PrivateRoute>
              <DashboardPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/transactions/new"
          element={
            <PrivateRoute>
              <TransactionPage />
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
