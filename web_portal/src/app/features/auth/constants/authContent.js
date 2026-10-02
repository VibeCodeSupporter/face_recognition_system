/**
 * Copy hiển thị của module auth (tiếng Anh) — tập trung ở đây để dễ rà soát
 * nội dung và chuẩn bị cho đa ngôn ngữ về sau.
 */

/** Nội dung của brand panel (cột trái các màn hình public). */
export const AUTH_BRAND_CONTENT = {
  features: [
    {
      key: 'users',
      iconKey: 'users',
      title: 'User & face management',
      description: 'Enroll, review and re-register face profiles for every user.',
    },
    {
      key: 'history',
      iconKey: 'history',
      title: 'Access history',
      description: 'Search and audit every entry decision synced from Edge devices.',
    },
    {
      key: 'devices',
      iconKey: 'devices',
      title: 'Device fleet',
      description: 'Track door devices, connectivity and synchronization status.',
    },
    {
      key: 'security',
      iconKey: 'security',
      title: 'Role-based access',
      description: 'Separate admin and operator permissions with audit trails.',
    },
  ],
  footerNote: 'Doors keep working offline — data syncs automatically once the connection returns.',
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
