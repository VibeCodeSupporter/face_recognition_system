import { ScanOutlined } from '@ant-design/icons'
import { APP_INFO } from '../constants/appInfo.js'
import cx from '../utils/cx.js'
import './BrandMark.css'

const SIZE_CLASS_NAMES = {
  sm: 'brand-mark--sm',
  md: 'brand-mark--md',
}

/**
 * Logo + Tên sản phẩm FaceAccess.
 * Khi collapsed = true, chỉ hiển thị logo icon để tránh tràn chữ trong sidebar thu gọn.
 *
 * @param {object} props
 * @param {'sm' | 'md'} [props.size]
 * @param {'light' | 'dark'} [props.tone]
 * @param {boolean} [props.collapsed]
 * @param {string} [props.className]
 */
export default function BrandMark({
  size = 'md',
  tone = 'dark',
  collapsed = false,
  className,
}) {
  return (
    <span
      className={cx(
        'brand-mark',
        SIZE_CLASS_NAMES[size],
        `brand-mark--${tone}`,
        collapsed && 'brand-mark--collapsed',
        className
      )}
    >
      <span className="brand-mark__logo" aria-label={APP_INFO.name}>
        <ScanOutlined />
      </span>
      {!collapsed && (
        <span className="brand-mark__text">
          <span className="brand-mark__name">{APP_INFO.name}</span>
          <span className="brand-mark__product">{APP_INFO.portalName}</span>
        </span>
      )}
    </span>
  )
}
