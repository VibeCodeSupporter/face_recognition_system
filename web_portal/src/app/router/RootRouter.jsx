import { useEffect } from 'react'
import { Spin } from 'antd'
import { ROUTES } from '../constants/routes.js'
import useHashRoute from '../hooks/useHashRoute.js'
import AppLayout from '../layouts/AppLayout.jsx'
import { useAuth } from '../providers/AuthProvider.jsx'

// Public Auth Pages
import ForgotPasswordPage from '../features/auth/pages/ForgotPasswordPage.jsx'
import LoginPage from '../features/auth/pages/LoginPage.jsx'
import RegisterPage from '../features/auth/pages/RegisterPage.jsx'

// Protected Feature Pages
import DashboardPage from '../features/dashboard/pages/DashboardPage.jsx'
import UsersPage from '../features/users/UsersPage.jsx'
import DevicesPage from '../features/devices/DevicesPage.jsx'
import SessionsPage from '../features/sessions/SessionsPage.jsx'
import LogsPage from '../features/accessLogs/LogsPage.jsx'

/**
 * Route công khai (render trong AuthLayout)
 */
const PUBLIC_ROUTES = {
  [ROUTES.LOGIN]: LoginPage,
  [ROUTES.REGISTER]: RegisterPage,
  [ROUTES.FORGOT_PASSWORD]: ForgotPasswordPage,
}

/**
 * Route yêu cầu đăng nhập (render trong AppLayout với sidebar/topbar)
 */
const PROTECTED_ROUTES = {
  [ROUTES.DASHBOARD]: DashboardPage,
  [ROUTES.USERS]: UsersPage,
  [ROUTES.DEVICES]: DevicesPage,
  [ROUTES.SESSIONS]: SessionsPage,
  [ROUTES.LOGS]: LogsPage,
}

export default function RootRouter() {
  const { path, navigate } = useHashRoute()
  const { isAuthenticated, isInitializing } = useAuth()

  const defaultRoute = isAuthenticated ? ROUTES.DASHBOARD : ROUTES.LOGIN
  const currentPath = path || defaultRoute

  const PublicPage = PUBLIC_ROUTES[currentPath]
  const ProtectedPage = PROTECTED_ROUTES[currentPath]

  useEffect(() => {
    if (isInitializing) return

    if (!isAuthenticated) {
      // Chưa đăng nhập mà đang ở trang protected hoặc hash không hợp lệ
      if (ProtectedPage || !PublicPage) {
        navigate(ROUTES.LOGIN, { replace: true })
      }
    } else {
      // Đã đăng nhập mà đang ở trang login/register/forgot hoặc hash không hợp lệ
      if (PublicPage || !ProtectedPage) {
        navigate(ROUTES.DASHBOARD, { replace: true })
      }
    }
  }, [isAuthenticated, isInitializing, PublicPage, ProtectedPage, navigate])

  if (isInitializing) {
    return (
      <div
        style={{
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
          backgroundColor: '#f5f7fa',
        }}
      >
        <Spin size="large" />
        <span style={{ color: '#8c8c8c', fontSize: 14 }}>
          Đang tải thông tin hệ thống FaceAccess...
        </span>
      </div>
    )
  }

  // Trường hợp CHƯA ĐĂNG NHẬP:
  if (!isAuthenticated) {
    const Component = PublicPage || LoginPage
    return <Component />
  }

  // Trường hợp ĐÃ ĐĂNG NHẬP:
  const Component = ProtectedPage || DashboardPage
  return (
    <AppLayout>
      <Component />
    </AppLayout>
  )
}
