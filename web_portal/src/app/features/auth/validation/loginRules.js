import { createEmailRules, createPasswordRules } from './fieldRules.js'

/** Rule validate cho form đăng nhập. */
export const loginFormRules = {
  email: createEmailRules(),
  password: createPasswordRules(),
}

export default loginFormRules
