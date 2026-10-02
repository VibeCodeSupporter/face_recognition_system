import AppLink from '../../../components/AppLink.jsx'
import { ROUTES } from '../../../constants/routes.js'
import AuthLayout from '../../../layouts/AuthLayout.jsx'
import AuthBrandPanel from '../components/AuthBrandPanel.jsx'
import AuthCard from '../components/AuthCard.jsx'
import ForgotPasswordForm from '../components/ForgotPasswordForm.jsx'
import { FORGOT_PASSWORD_COPY } from '../constants/authContent.js'

/**
 * Page quên mật khẩu — vùng PUBLIC (`#/forgot-password`).
 * Trạng thái "đã gửi email" nằm trong ForgotPasswordForm (ResetLinkSentPanel).
 */
export default function ForgotPasswordPage() {
  return (
    <AuthLayout aside={<AuthBrandPanel />}>
      <AuthCard
        title={FORGOT_PASSWORD_COPY.title}
        description={FORGOT_PASSWORD_COPY.description}
        footer={
          <>
            Remembered your password? <AppLink to={ROUTES.LOGIN}>Back to sign in</AppLink>
          </>
        }
      >
        <ForgotPasswordForm />
      </AuthCard>
    </AuthLayout>
  )
}
