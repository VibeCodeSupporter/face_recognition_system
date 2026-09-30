import { useState } from 'react'
import { LockOutlined, MailOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Checkbox, Form, Input } from 'antd'
import AppLink from '../../../components/AppLink.jsx'
import { ROUTES } from '../../../constants/routes.js'
import { ANTD_VALIDATE_MESSAGES } from '../../../constants/validationMessages.js'
import useHashRoute from '../../../hooks/useHashRoute.js'
import simulateRequest from '../../../utils/simulateRequest.js'
import { loginFormRules } from '../validation/loginRules.js'
import './AuthForm.css'

/**
 * Form đăng nhập của Web Portal.
 * Hiện mới là UI + validate client-side; bước gọi Backend Server sẽ được
 * nối ở tầng services (đánh dấu bằng TODO(api)).
 */
export default function LoginForm() {
  const { navigate } = useHashRoute()
  const { message } = AntdApp.useApp()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const handleFinish = async (values) => {
    setSubmitError('')
    setIsSubmitting(true)

    try {
      // TODO(api): thay bằng authService.login(values) khi Backend Server sẵn sàng.
      await simulateRequest({ email: values.email, remember: values.remember })
      message.success('Signed in successfully')
      navigate(ROUTES.DASHBOARD)
    } catch (error) {
      setSubmitError(error.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Form
      className="auth-form"
      name="login"
      layout="vertical"
      requiredMark={false}
      validateMessages={ANTD_VALIDATE_MESSAGES}
      scrollToFirstError
      onFinish={handleFinish}
    >
      {submitError ? (
        <Alert className="auth-form__alert" type="error" showIcon title={submitError} />
      ) : null}

      <Form.Item name="email" label="Work email" rules={loginFormRules.email}>
        <Input
          size="large"
          prefix={<MailOutlined />}
          placeholder="you@company.com"
          autoComplete="username"
          inputMode="email"
        />
      </Form.Item>

      <Form.Item name="password" label="Password" rules={loginFormRules.password}>
        <Input.Password
          size="large"
          prefix={<LockOutlined />}
          placeholder="Enter your password"
          autoComplete="current-password"
        />
      </Form.Item>

      <div className="auth-form__row">
        <Form.Item name="remember" valuePropName="checked" initialValue={false} noStyle>
          <Checkbox>Remember me</Checkbox>
        </Form.Item>
        <AppLink to={ROUTES.FORGOT_PASSWORD}>Forgot password?</AppLink>
      </div>

      <Button
        className="auth-form__submit"
        type="primary"
        size="large"
        htmlType="submit"
        block
        loading={isSubmitting}
      >
        Sign in
      </Button>
    </Form>
  )
}
