import { createEmailRules } from './fieldRules.js'

/** Rule validate cho form quên mật khẩu. */
export const forgotPasswordFormRules = {
  email: createEmailRules(),
}

export default forgotPasswordFormRules
