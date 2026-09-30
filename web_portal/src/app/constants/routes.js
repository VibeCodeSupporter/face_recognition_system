/**
 * Danh sách route của Web Portal.
 *
 * Dự án dùng hash routing (xem app/hooks/useHashRoute.js) vì stack hiện tại
 * chưa có react-router — khi tích hợp router chính thức chỉ cần đổi giá trị
 * ở đây, page/link không phải sửa.
 */
export const ROUTES = {
  /** Vùng PUBLIC — chưa đăng nhập */
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',

  /** Vùng PROTECTED — cần đăng nhập (guard sẽ bật khi có API auth) */
  DASHBOARD: '/dashboard',
}

/** Route mặc định khi hash trống. */
export const DEFAULT_ROUTE = ROUTES.LOGIN

export default ROUTES
