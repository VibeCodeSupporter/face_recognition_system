import AuthLayout from '../../../layouts/AuthLayout.jsx'
import AuthBrandPanel from '../components/AuthBrandPanel.jsx'
import LoginForm from '../components/LoginForm.jsx'

/**
 * Trang đăng nhập Quản trị viên FaceAccess
 */
export default function LoginPage() {
  return (
    <AuthLayout aside={<AuthBrandPanel />}>
      <div
        style={{
          width: '100%',
          maxWidth: 420,
          margin: '0 auto',
          padding: '36px 32px',
          background: '#ffffff',
          borderRadius: 16,
          boxShadow: '0 10px 30px -5px rgba(2, 132, 199, 0.12), 0 4px 12px -2px rgba(234, 179, 8, 0.08)',
          border: '1px solid #e0f2fe',
        }}
      >
        <LoginForm />
      </div>
    </AuthLayout>
  )
}
