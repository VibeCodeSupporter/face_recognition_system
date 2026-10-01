import {
  FULL_NAME_MAX_LENGTH,
  FULL_NAME_MIN_LENGTH,
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
} from './passwordPolicy.js'

/**
 * Toàn bộ message validate của portal (tiếng Anh).
 * Tập trung ở một chỗ để đổi text/đa ngôn ngữ sau này không phải sửa rải rác
 * trong component.
 */
export const VALIDATION_MESSAGES = {
  emailRequired: 'Enter your work email address',
  emailInvalid: 'Enter a valid email address',
  passwordRequired: 'Enter your password',
  passwordTooShort: `Password must be at least ${PASSWORD_MIN_LENGTH} characters`,
  passwordTooLong: `Password must be at most ${PASSWORD_MAX_LENGTH} characters`,
  passwordComplexity: 'Password does not meet all requirements below',
  confirmPasswordRequired: 'Confirm your password',
  confirmPasswordMismatch: 'Passwords do not match',
  fullNameRequired: 'Enter your full name',
  fullNameTooShort: `Full name must be at least ${FULL_NAME_MIN_LENGTH} characters`,
  fullNameTooLong: `Full name must be at most ${FULL_NAME_MAX_LENGTH} characters`,
  termsRequired: 'Accept the Terms of Service to continue',
}

/**
 * Message mặc định cho các rule sinh tự động của antd Form
 * (dùng khi không truyền `message` riêng).
 */
export const ANTD_VALIDATE_MESSAGES = {
  required: '${label} is required',
  types: {
    email: VALIDATION_MESSAGES.emailInvalid,
    string: '${label} must be text',
  },
  string: {
    min: '${label} must be at least ${min} characters',
    max: '${label} must be at most ${max} characters',
  },
}

export default VALIDATION_MESSAGES
