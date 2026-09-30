import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons'
import { PASSWORD_REQUIREMENTS } from '../../../constants/passwordPolicy.js'
import cx from '../../../utils/cx.js'
import evaluatePasswordStrength from '../../../utils/passwordStrength.js'
import './PasswordStrengthMeter.css'

/**
 * Hiển thị độ mạnh mật khẩu theo thời gian thực: thanh 4 mức + checklist các
 * yêu cầu. Toàn bộ nhãn/yêu cầu lấy từ constants/passwordPolicy.js nên UI và
 * validation luôn khớp nhau.
 *
 * @param {object} props
 * @param {string} [props.value] - mật khẩu đang nhập
 */
export default function PasswordStrengthMeter({ value = '' }) {
  const { score, level, requirements } = evaluatePasswordStrength(value)

  return (
    <div className={cx('password-strength', `password-strength--${level.tone}`)} aria-live="polite">
      <div className="password-strength__header">
        <span>Password strength</span>
        <span className="password-strength__level">{level.label}</span>
      </div>

      <div className="password-strength__meter">
        {PASSWORD_REQUIREMENTS.map((requirement, index) => (
          <span
            key={requirement.key}
            className={cx('password-strength__segment', index < score && 'is-filled')}
          />
        ))}
      </div>

      <ul className="password-strength__list">
        {requirements.map((requirement) => (
          <li
            key={requirement.key}
            className={cx('password-strength__item', requirement.isMet && 'is-met')}
          >
            {requirement.isMet ? <CheckCircleFilled /> : <CloseCircleFilled />}
            <span>{requirement.label}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
