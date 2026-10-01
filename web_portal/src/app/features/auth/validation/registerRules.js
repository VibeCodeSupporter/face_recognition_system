import {
  createConfirmPasswordRules,
  createEmailRules,
  createFullNameRules,
  createPasswordRules,
  createTermsRule,
} from './fieldRules.js'

/** Rule validate cho form đăng ký. */
export const registerFormRules = {
  fullName: createFullNameRules(),
  email: createEmailRules(),
  password: createPasswordRules({ requireComplexity: true }),
  confirmPassword: createConfirmPasswordRules(),
  acceptTerms: [createTermsRule()],
}

export default registerFormRules
