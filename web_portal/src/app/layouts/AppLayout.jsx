import { LogoutOutlined } from '@ant-design/icons'
import { Button, Tooltip } from 'antd'
import BrandMark from '../components/BrandMark.jsx'
import { ROUTES } from '../constants/routes.js'
import useHashRoute from '../hooks/useHashRoute.js'
import './AppLayout.css'

/**
 * Khung cho vùng PROTECTED (sau đăng nhập): topbar + vùng nội dung.
 * Sidebar/navigation đầy đủ sẽ được bổ sung khi các module nghiệp vụ
 * (users, devices, access history) hoàn thành.
 *
 * @param {{ children: React.ReactNode }} props
 */
export default function AppLayout({ children }) {
  const { navigate } = useHashRoute()

  // TODO(auth): thay bằng logout() của AuthProvider khi có API đăng nhập.
  const handleSignOut = () => {
    navigate(ROUTES.LOGIN)
  }

  return (
    <div className="app-layout">
      <header className="app-layout__topbar">
        <div className="app-layout__topbar-inner u-content-max-width">
          <BrandMark size="sm" />
          <Tooltip title="Sign out">
            <Button
              type="text"
              icon={<LogoutOutlined />}
              onClick={handleSignOut}
              aria-label="Sign out"
            >
              <span className="app-layout__signout-label">Sign out</span>
            </Button>
          </Tooltip>
        </div>
      </header>

      <main className="app-layout__content u-content-max-width">{children}</main>
    </div>
  )
}
