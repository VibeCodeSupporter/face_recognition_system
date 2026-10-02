import cx from '../utils/cx.js'

/**
 * Link điều hướng nội bộ của portal (hash routing).
 * Dùng thay cho thẻ `<a href="/...">` để không reload trang.
 *
 * @param {object} props
 * @param {string} props.to - route đích (lấy từ app/constants/routes.js)
 * @param {React.ReactNode} props.children
 * @param {string} [props.className]
 */
export default function AppLink({ to, children, className, ...restProps }) {
  return (
    <a className={cx('app-link', className)} href={`#${to}`} {...restProps}>
      {children}
    </a>
  )
}
