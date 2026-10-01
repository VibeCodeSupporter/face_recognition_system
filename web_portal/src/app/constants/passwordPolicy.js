/** Giới hạn độ dài mật khẩu (dùng chung cho rule validate và UI). */
export const PASSWORD_MIN_LENGTH = 8
export const PASSWORD_MAX_LENGTH = 64

/** Giới hạn độ dài họ tên. */
export const FULL_NAME_MIN_LENGTH = 2
export const FULL_NAME_MAX_LENGTH = 60

/**
 * Các yêu cầu mật khẩu — mỗi yêu cầu có `test` để tái sử dụng cho cả
 * validate form lẫn meter hiển thị độ mạnh. Thêm yêu cầu mới chỉ cần thêm
 * một phần tử ở đây, UI và validation tự cập nhật theo.
 */
export const PASSWORD_REQUIREMENTS = [
  {
    key: 'length',
    label: `At least ${PASSWORD_MIN_LENGTH} characters`,
    test: (value) => value.length >= PASSWORD_MIN_LENGTH,
  },
  {
    key: 'letterCase',
    label: 'Upper and lower case letters',
    test: (value) => /[a-z]/.test(value) && /[A-Z]/.test(value),
  },
  {
    key: 'number',
    label: 'At least one number',
    test: (value) => /\d/.test(value),
  },
  {
    key: 'symbol',
    label: 'At least one symbol',
    test: (value) => /[^A-Za-z0-9]/.test(value),
  },
]

/**
 * Nhãn hiển thị theo số yêu cầu đã đạt (score 0 → 4).
 * `tone` dùng làm data-attribute cho CSS tô màu.
 */
export const PASSWORD_STRENGTH_LEVELS = [
  { score: 0, label: 'Very weak', tone: 'danger' },
  { score: 1, label: 'Weak', tone: 'danger' },
  { score: 2, label: 'Fair', tone: 'warning' },
  { score: 3, label: 'Good', tone: 'info' },
  { score: 4, label: 'Strong', tone: 'success' },
]

export default PASSWORD_REQUIREMENTS
