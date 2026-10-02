import AppLink from '../../../components/AppLink.jsx'
import { ROUTES } from '../../../constants/routes.js'
import AuthLayout from '../../../layouts/AuthLayout.jsx'
import AuthBrandPanel from '../components/AuthBrandPanel.jsx'
import AuthCard from '../components/AuthCard.jsx'
import RegisterForm from '../components/RegisterForm.jsx'

/**
 * Page đăng ký — vùng PUBLIC (`#/register`).
 */
export default function RegisterPage() {
  return (
    <AuthLayout aside={<AuthBrandPanel />}>
      <AuthCard
        title="Create an account"
        description="Register an operator account for the portal. An administrator approves the account before it can sign in."
        footer={
          <>
            Already have an account? <AppLink to={ROUTES.LOGIN}>Sign in</AppLink>
          </>
        }
      >
        <RegisterForm />
      </AuthCard>
    </AuthLayout>
  )
}
