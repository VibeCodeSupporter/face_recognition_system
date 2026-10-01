import { Button, Result } from 'antd'
import { FORGOT_PASSWORD_COPY } from '../constants/authContent.js'
import './ResetLinkSentPanel.css'

/**
 * Trạng thái "đã gửi email đặt lại mật khẩu" của màn hình quên mật khẩu.
 *
 * @param {object} props
 * @param {string} props.email - email người dùng vừa nhập
 * @param {boolean} props.isResending - đang gửi lại
 * @param {() => void} props.onResend - gửi lại link đặt lại
 */
export default function ResetLinkSentPanel({ email, isResending, onResend }) {
  return (
    <Result
      className="auth-result"
      status="success"
      title={FORGOT_PASSWORD_COPY.sentTitle}
      subTitle={FORGOT_PASSWORD_COPY.buildSentDescription(email)}
      extra={
        <Button type="primary" loading={isResending} onClick={onResend}>
          Resend reset link
        </Button>
      }
    />
  )
}
