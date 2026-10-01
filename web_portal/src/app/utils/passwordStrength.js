import { PASSWORD_REQUIREMENTS, PASSWORD_STRENGTH_LEVELS } from '../constants/passwordPolicy.js'

/**
 * Đánh giá độ mạnh mật khẩu dựa trên PASSWORD_REQUIREMENTS.
 * Hàm thuần (pure) nên dùng được cho cả validate form và hiển thị UI.
 *
 * @param {string} password
 * @returns {{
 *   score: number,
 *   level: { score: number, label: string, tone: string },
 *   requirements: Array<{ key: string, label: string, isMet: boolean }>,
 *   isStrongEnough: boolean,
 * }}
 */
export default function evaluatePasswordStrength(password = '') {
  const requirements = PASSWORD_REQUIREMENTS.map((requirement) => ({
    key: requirement.key,
    label: requirement.label,
    isMet: password.length > 0 && requirement.test(password),
  }))

  const score = requirements.filter((requirement) => requirement.isMet).length
  const level =
    PASSWORD_STRENGTH_LEVELS.find((item) => item.score === score) ??
    PASSWORD_STRENGTH_LEVELS[0]

  return {
    score,
    level,
    requirements,
    isStrongEnough: score === PASSWORD_REQUIREMENTS.length,
  }
}
