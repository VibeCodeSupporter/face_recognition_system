import { useState } from 'react'
import {
  LockOutlined,
  LoginOutlined,
  ScanOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Form, Input, Typography } from 'antd'
import { ROUTES } from '../../../constants/routes.js'
import useHashRoute from '../../../hooks/useHashRoute.js'
import { useAuth } from '../../../providers/AuthProvider.jsx'
import { getErrorMessage } from '../../../services/apiClient.js'
import './AuthForm.css'

const { Title, Text } = Typography

export default function LoginForm() {
  const { navigate } = useHashRoute()
  const { message } = AntdApp.useApp()
  const { login } = useAuth()

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const handleAdminLogin = async (values) => {
    setSubmitError('')
    setIsSubmitting(true)
    try {
      const data = await login(values.username.trim(), values.password)
      message.success(`Đăng nhập thành công! Chào mừng ${data.admin?.full_name || values.username}.`)
      navigate(ROUTES.DASHBOARD)
    } catch (error) {
      setSubmitError(getErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-form-container" style={{ width: '100%' }}>
      {/* Header Logo & Title trong Form Card */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          marginBottom: 28,
        }}
      >
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: 18,
            background: 'linear-gradient(135deg, #0284c7 0%, #38bdf8 55%, #eab308 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ffffff',
            fontSize: 32,
            boxShadow: '0 8px 24px rgba(2, 132, 199, 0.35)',
            marginBottom: 16,
          }}
        >
          <ScanOutlined />
        </div>
        <Title level={2} style={{ margin: 0, color: '#0f172a', fontWeight: 800 }}>
          FaceAccess
        </Title>
        <Text type="secondary" style={{ fontSize: 14, marginTop: 4, color: '#475569' }}>
          Hệ thống Kiểm soát Ra vào &amp; Nhận diện Khuôn mặt
        </Text>
      </div>

      {submitError ? (
        <Alert
          className="auth-form__alert"
          type="error"
          showIcon
          title="Đăng nhập không thành công"
          description={<span style={{ whiteSpace: 'pre-line' }}>{submitError}</span>}
          style={{ marginBottom: 20 }}
          closable
          onClose={() => setSubmitError('')}
        />
      ) : null}

      <Form
        name="login_form"
        layout="vertical"
        requiredMark={false}
        onFinish={handleAdminLogin}
      >
        <Form.Item
          name="username"
          label={<span style={{ fontWeight: 600, color: '#334155' }}>Tên đăng nhập</span>}
          rules={[{ required: true, message: 'Vui lòng nhập tên tài khoản!' }]}
        >
          <Input
            size="large"
            prefix={<UserOutlined style={{ color: '#0284c7', marginRight: 4 }} />}
            placeholder="Nhập tên tài khoản quản trị"
            autoComplete="username"
            style={{ borderRadius: 10, height: 46 }}
          />
        </Form.Item>

        <Form.Item
          name="password"
          label={<span style={{ fontWeight: 600, color: '#334155' }}>Mật khẩu</span>}
          rules={[{ required: true, message: 'Vui lòng nhập mật khẩu!' }]}
        >
          <Input.Password
            size="large"
            prefix={<LockOutlined style={{ color: '#eab308', marginRight: 4 }} />}
            placeholder="Nhập mật khẩu an toàn"
            autoComplete="current-password"
            style={{ borderRadius: 10, height: 46 }}
          />
        </Form.Item>

        <Button
          type="primary"
          size="large"
          htmlType="submit"
          icon={<LoginOutlined />}
          block
          loading={isSubmitting}
          style={{
            height: 48,
            fontSize: 16,
            fontWeight: 700,
            borderRadius: 10,
            backgroundColor: '#0284c7',
            boxShadow: '0 4px 14px rgba(2, 132, 199, 0.35)',
            marginTop: 12,
          }}
        >
          Đăng nhập hệ thống
        </Button>
      </Form>
    </div>
  )
}
