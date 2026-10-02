import { useState } from 'react'
import { LockOutlined, MailOutlined, UserOutlined } from '@ant-design/icons'
import { App as AntdApp, Button, Checkbox, Form, Input } from 'antd'
import { ROUTES } from '../../../constants/routes.js'
import { ANTD_VALIDATE_MESSAGES } from '../../../constants/validationMessages.js'
import useHashRoute from '../../../hooks/useHashRoute.js'
import simulateRequest from '../../../utils/simulateRequest.js'
import { registerFormRules } from '../validation/registerRules.js'
import PasswordStrengthMeter from './PasswordStrengthMeter.jsx'
import './AuthForm.css'

const LEGAL_DOCUMENTS = {
  termsOfService: 'Terms of Service',
  privacyPolicy: 'Privacy Policy',
}

/**
 * Form đăng ký tài khoản portal cho operator/admin.
 * Có meter độ mạnh mật khẩu và validate khớp mật khẩu ngay ở client.
 */
export default function RegisterForm() {
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { navigate } = useHashRoute()
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Theo dõi giá trị password để meter cập nhật theo thời gian thực
  const passwordValue = Form.useWatch('password', form)

  const handleFinish = async (values) => {
    setIsSubmitting(true)

    try {
      // TODO(api): thay bằng authService.register(values); tài khoản cần được
      // admin duyệt trước khi kích hoạt (theo mô hình RBAC của hệ thống).
      await simulateRequest(values)
      message.success('Account created — an administrator will approve it shortly')
      navigate(ROUTES.LOGIN)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleOpenLegalDocument = (documentName) => () => {
    message.info(`${documentName} will be published with the portal release`)
  }

  return (
    <Form
      className="auth-form"
      form={form}
      name="register"
      layout="vertical"
      requiredMark={false}
      validateMessages={ANTD_VALIDATE_MESSAGES}
      scrollToFirstError
      onFinish={handleFinish}
    >
      <Form.Item name="fullName" label="Full name" rules={registerFormRules.fullName}>
        <Input
          size="large"
          prefix={<UserOutlined />}
          placeholder="Nguyen Van A"
          autoComplete="name"
        />
      </Form.Item>

      <Form.Item name="email" label="Work email" rules={registerFormRules.email}>
        <Input
          size="large"
          prefix={<MailOutlined />}
          placeholder="you@company.com"
          autoComplete="email"
          inputMode="email"
        />
      </Form.Item>

      <Form.Item
        name="password"
        label="Password"
        rules={registerFormRules.password}
        extra={passwordValue ? <PasswordStrengthMeter value={passwordValue} /> : null}
      >
        <Input.Password
          size="large"
          prefix={<LockOutlined />}
          placeholder="Create a password"
          autoComplete="new-password"
        />
      </Form.Item>

      <Form.Item
        name="confirmPassword"
        label="Confirm password"
        rules={registerFormRules.confirmPassword}
        dependencies={['password']}
      >
        <Input.Password
          size="large"
          prefix={<LockOutlined />}
          placeholder="Repeat your password"
          autoComplete="new-password"
        />
      </Form.Item>

      <Form.Item
        className="auth-form__terms"
        name="acceptTerms"
        valuePropName="checked"
        rules={registerFormRules.acceptTerms}
      >
        <Checkbox>
          I agree to the{' '}
          <button
            type="button"
            className="auth-form__link-button"
            onClick={handleOpenLegalDocument(LEGAL_DOCUMENTS.termsOfService)}
          >
            {LEGAL_DOCUMENTS.termsOfService}
          </button>{' '}
          and{' '}
          <button
            type="button"
            className="auth-form__link-button"
            onClick={handleOpenLegalDocument(LEGAL_DOCUMENTS.privacyPolicy)}
          >
            {LEGAL_DOCUMENTS.privacyPolicy}
          </button>
        </Checkbox>
      </Form.Item>

      <Button
        className="auth-form__submit"
        type="primary"
        size="large"
        htmlType="submit"
        block
        loading={isSubmitting}
      >
        Create account
      </Button>
    </Form>
  )
}
