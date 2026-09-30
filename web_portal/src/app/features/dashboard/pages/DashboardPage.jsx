import { ScanOutlined } from '@ant-design/icons'
import { Button, Card, Result } from 'antd'
import { ROUTES } from '../../../constants/routes.js'
import useHashRoute from '../../../hooks/useHashRoute.js'
import './DashboardPage.css'

/**
 * Page mặc định của vùng PROTECTED (`#/dashboard`).
 * Hiện là placeholder để hoàn thiện luồng điều hướng sau đăng nhập; dashboard
 * nghiệp vụ (số liệu, người dùng, thiết bị, lịch sử ra vào) sẽ được bổ sung
 * theo từng module.
 */
export default function DashboardPage() {
  const { navigate } = useHashRoute()

  return (
    <Card className="dashboard-page" variant="outlined">
      <Result
        className="dashboard-page__result"
        icon={<ScanOutlined />}
        title="Portal shell is ready"
        subTitle="The sign-in flow works end to end. Dashboard metrics, user management, device fleet and access history will be connected to the Cloud API in the next iterations."
        extra={
          <Button type="primary" onClick={() => navigate(ROUTES.LOGIN)}>
            Back to sign in
          </Button>
        }
      />
    </Card>
  )
}
