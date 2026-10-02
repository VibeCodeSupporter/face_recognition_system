import { useState } from 'react'
import { MailOutlined } from '@ant-design/icons'
import { App as AntdApp, Button, Form, Input } from 'antd'
import { ANTD_VALIDATE_MESSAGES } from '../../../constants/validationMessages.js'
import simulateRequest from '../../../utils/simulateRequest.js'
import { forgotPasswordFormRules } from '../validation/forgotPasswordRules.js'
import ResetLinkSentPanel from './ResetLinkSentPanel.jsx'
import './AuthForm.css'

/**
 * Form quên mật khẩu: nhập email → gửi link đặt lại.
 * Sau khi submit thành công, form chuyển sang trạng thái
 * ResetLinkSentPanel (có thể gửi lại link).
 */
export default function ForgotPasswordForm() {
  const { message } = AntdApp.useApp()
  const [submittedEmail, setSubmittedEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isResending, setIsResending] = useState(false)

  const handleFinish = async (values) => {
    setIsSubmitting(true)

    try {
      // TODO(api): thay bằng authService.requestPasswordReset(values).
      await simulateRequest(values)
      setSubmittedEmail(values.email)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleResend = async () => {
    setIsResending(true)

    try {
      await simulateRequest({ email: submittedEmail })
      message.success('Reset link sent again')
    } finally {
      setIsResending(false)
    }
  }

  if (submittedEmail) {
    return (
      <ResetLinkSentPanel
        email={submittedEmail}
        isResending={isResending}
        onResend={handleResend}
      />
    )
  }

  return (
    <Form
      className="auth-form"
      name="forgotPassword"
      layout="vertical"
      requiredMark={false}
      validateMessages={ANTD_VALIDATE_MESSAGES}
      scrollToFirstError
      onFinish={handleFinish}
    >
      <Form.Item name="email" label="Work email" rules={forgotPasswordFormRules.email}>
        <Input
          size="large"
          prefix={<MailOutlined />}
          placeholder="you@company.com"
          autoComplete="email"
          inputMode="email"
        />
      </Form.Item>

      <Button
        className="auth-form__submit"
        type="primary"
        size="large"
        htmlType="submit"
        block
        loading={isSubmitting}
      >
        Send reset link
      </Button>
    </Form>
  )
}
