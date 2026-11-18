/**
 * Copy hiển thị của module auth (tiếng Anh) — tập trung ở đây để dễ rà soát
 * nội dung và chuẩn bị cho đa ngôn ngữ về sau.
 */

/** Nội dung của brand panel trên các màn hình public. */
export const AUTH_BRAND_CONTENT = {
  features: [
    {
      key: 'users',
      iconKey: 'users',
      title: 'Quản lý nhân sự',
      description: 'Đăng ký và quản lý hồ sơ khuôn mặt.',
    },
    {
      key: 'history',
      iconKey: 'history',
      title: 'Lịch sử ra vào',
      description: 'Theo dõi các lượt xác thực tại cửa.',
    },
    {
      key: 'devices',
      iconKey: 'devices',
      title: 'Thiết bị thông minh',
      description: 'Giám sát trạng thái và kết nối thiết bị.',
    },
    {
      key: 'security',
      iconKey: 'security',
      title: 'Bảo mật nhiều lớp',
      description: 'Phân quyền và lưu lại hoạt động hệ thống.',
    },
  ],
  footerNote: 'Hệ thống kiểm soát ra vào FaceAccess.',
}

/** Nội dung riêng của màn hình quên mật khẩu. */
export const FORGOT_PASSWORD_COPY = {
  title: 'Forgot password',
  description: 'Enter the email address linked to your portal account and we will send a reset link.',
  sentTitle: 'Check your inbox',
  buildSentDescription: (email) =>
    `If an account exists for ${email}, a password reset link is on its way. The link expires in 30 minutes.`,
}

export default AUTH_BRAND_CONTENT
