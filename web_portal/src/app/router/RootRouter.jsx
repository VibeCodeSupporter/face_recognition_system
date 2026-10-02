import { useEffect } from 'react'
import { DEFAULT_ROUTE, ROUTES } from '../constants/routes.js'
import useHashRoute from '../hooks/useHashRoute.js'
import AppLayout from '../layouts/AppLayout.jsx'
import ForgotPasswordPage from '../features/auth/pages/ForgotPasswordPage.jsx'
import LoginPage from '../features/auth/pages/LoginPage.jsx'
import RegisterPage from '../features/auth/pages/RegisterPage.jsx'
import DashboardPage from '../features/dashboard/pages/DashboardPage.jsx'

/**
 * Route công khai (chưa đăng nhập) — render trong AuthLayout.
 * Khi tích hợp API auth, các route protected sẽ được bọc bởi RequireAuth.
 */
const PUBLIC_ROUTES = {
  [ROUTES.LOGIN]: LoginPage,
  [ROUTES.REGISTER]: RegisterPage,
  [ROUTES.FORGOT_PASSWORD]: ForgotPasswordPage,
}

/** Route yêu cầu đăng nhập — render trong AppLayout (sidebar/topbar). */
const PROTECTED_ROUTES = {
  [ROUTES.DASHBOARD]: DashboardPage,
}

/**
 * Điểm phân tuyến duy nhất của ứng dụng.
 * App.jsx chỉ mount component này, không chứa logic page.
 */
export default function RootRouter() {
  const { path, navigate } = useHashRoute()
  const currentPath = path || DEFAULT_ROUTE
  const PublicPage = PUBLIC_ROUTES[currentPath]
  const ProtectedPage = PROTECTED_ROUTES[currentPath]

  useEffect(() => {
    const isKnownRoute = Boolean(PublicPage || ProtectedPage)

    if (!isKnownRoute) {
      navigate(DEFAULT_ROUTE, { replace: true })
    }
    // TODO(auth): khi có API đăng nhập, bật guard tại đây:
    // chưa đăng nhập + route protected  → điều hướng về ROUTES.LOGIN
    // đã đăng nhập + route public       → điều hướng về ROUTES.DASHBOARD
  }, [PublicPage, ProtectedPage, navigate])

  if (PublicPage) {
    return <PublicPage />
  }

  if (ProtectedPage) {
    return (
      <AppLayout>
        <ProtectedPage />
      </AppLayout>
    )
  }

  return null
}
