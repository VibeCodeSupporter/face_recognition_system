import {
  FULL_NAME_MAX_LENGTH,
  FULL_NAME_MIN_LENGTH,
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
} from '../../../constants/passwordPolicy.js'
import { VALIDATION_MESSAGES } from '../../../constants/validationMessages.js'
import evaluatePasswordStrength from '../../../utils/passwordStrength.js'

/**
 * Các "builder" rule dùng chung cho mọi form của module auth.
 * Mỗi form chỉ compose lại các rule này (xem loginRules/registerRules/...)
 * nên nội dung validate không bị lặp giữa các màn hình.
 */

/** @returns {import('antd').FormRule[]} */
export function createEmailRules() {
  return [
    { required: true, message: VALIDATION_MESSAGES.emailRequired, whitespace: true },
    { type: 'email', message: VALIDATION_MESSAGES.emailInvalid },
  ]
}

/**
 * @param {object} [options]
 * @param {boolean} [options.requireComplexity] - yêu cầu đạt toàn bộ PASSWORD_REQUIREMENTS
 * @returns {import('antd').FormRule[]}
 */
export function createPasswordRules({ requireComplexity = false } = {}) {
  const rules = [
    { required: true, message: VALIDATION_MESSAGES.passwordRequired },
    { min: PASSWORD_MIN_LENGTH, message: VALIDATION_MESSAGES.passwordTooShort },
    { max: PASSWORD_MAX_LENGTH, message: VALIDATION_MESSAGES.passwordTooLong },
  ]

  if (requireComplexity) {
    rules.push({
      validator: (_, value) => {
        if (!value) {
          return Promise.resolve()
        }

        return evaluatePasswordStrength(value).isStrongEnough
          ? Promise.resolve()
          : Promise.reject(new Error(VALIDATION_MESSAGES.passwordComplexity))
      },
    })
  }

  return rules
}

/** So khớp với field `password` của cùng form. */
export function createConfirmPasswordRules() {
  return [
    { required: true, message: VALIDATION_MESSAGES.confirmPasswordRequired },
    ({ getFieldValue }) => ({
      validator: (_, value) =>
        !value || value === getFieldValue('password')
          ? Promise.resolve()
          : Promise.reject(new Error(VALIDATION_MESSAGES.confirmPasswordMismatch)),
    }),
  ]
}

/** Họ tên: bắt buộc + giới hạn độ dài. */
export function createFullNameRules() {
  return [
    { required: true, message: VALIDATION_MESSAGES.fullNameRequired, whitespace: true },
    { min: FULL_NAME_MIN_LENGTH, message: VALIDATION_MESSAGES.fullNameTooShort },
    { max: FULL_NAME_MAX_LENGTH, message: VALIDATION_MESSAGES.fullNameTooLong },
  ]
}

/** Checkbox điều khoản: buộc phải tick. */
export function createTermsRule() {
  return {
    validator: (_, value) =>
      value ? Promise.resolve() : Promise.reject(new Error(VALIDATION_MESSAGES.termsRequired)),
  }
}
