/**
 * Danh sách route của Web Portal FaceAccess.
 * Sử dụng Hash Routing (`#/path`).
 */
export const ROUTES = {
  /** Vùng PUBLIC — chưa đăng nhập */
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',

  /** Vùng PROTECTED — quản trị hệ thống */
  DASHBOARD: '/dashboard',
  USERS: '/users',
  DEVICES: '/devices',
  SESSIONS: '/sessions',
  LOGS: '/logs',
  DELETION_HISTORY: '/deletion-history',
}

/** Route mặc định khi chưa đăng nhập */
export const DEFAULT_ROUTE = ROUTES.LOGIN

export default ROUTES
