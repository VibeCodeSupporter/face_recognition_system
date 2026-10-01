import AppLink from '../../../components/AppLink.jsx'
import { ROUTES } from '../../../constants/routes.js'
import AuthLayout from '../../../layouts/AuthLayout.jsx'
import AuthBrandPanel from '../components/AuthBrandPanel.jsx'
import AuthCard from '../components/AuthCard.jsx'
import LoginForm from '../components/LoginForm.jsx'

/**
 * Page đăng nhập — vùng PUBLIC (`#/login`).
 * Chỉ chịu trách nhiệm ghép khung + form, không chứa logic validate.
 */
export default function LoginPage() {
  return (
    <AuthLayout aside={<AuthBrandPanel />}>
      <AuthCard
        title="Sign in"
        description="Use your portal account to manage users, face enrollment, devices and access history."
        footer={
          <>
            New to the portal? <AppLink to={ROUTES.REGISTER}>Create an account</AppLink>
          </>
        }
      >
        <LoginForm />
      </AuthCard>
    </AuthLayout>
  )
}
