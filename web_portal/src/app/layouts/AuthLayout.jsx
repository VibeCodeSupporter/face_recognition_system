import './AuthLayout.css'

/**
 * Khung (shell) cho toàn bộ màn hình vùng PUBLIC: đăng nhập, đăng ký,
 * quên mật khẩu.
 *
 * - Desktop (≥ 1024px): 2 cột — brand panel bên trái, form bên phải.
 * - Tablet / mobile: 1 cột — brand panel thu gọn thành banner trên cùng.
 *
 * Layout generic, không biết gì về nội dung form (nhận qua `aside`/`children`).
 *
 * @param {object} props
 * @param {React.ReactNode} props.aside - khối thương hiệu (brand panel)
 * @param {React.ReactNode} props.children - nội dung form
 */
export default function AuthLayout({ aside, children }) {
  return (
    <div className="auth-layout">
      <aside className="auth-layout__aside">{aside}</aside>
      <main className="auth-layout__main">
        <div className="auth-layout__content">{children}</div>
      </main>
    </div>
  )
}
