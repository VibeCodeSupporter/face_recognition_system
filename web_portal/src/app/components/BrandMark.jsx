import { ScanOutlined } from '@ant-design/icons'
import { APP_INFO } from '../constants/appInfo.js'
import cx from '../utils/cx.js'
import './BrandMark.css'

const SIZE_CLASS_NAMES = {
  sm: 'brand-mark--sm',
  md: 'brand-mark--md',
}

/**
 * Logo + tên sản phẩm, dùng ở brand panel (nền gradient) và header vùng protected.
 *
 * @param {object} props
 * @param {'sm' | 'md'} [props.size]
 * @param {'light' | 'dark'} [props.tone] - `light` khi nền tối, `dark` khi nền sáng
 * @param {string} [props.className]
 */
export default function BrandMark({ size = 'md', tone = 'dark', className }) {
  return (
    <span className={cx('brand-mark', SIZE_CLASS_NAMES[size], `brand-mark--${tone}`, className)}>
      <span className="brand-mark__logo" aria-hidden="true">
        <ScanOutlined />
      </span>
      <span className="brand-mark__text">
        <span className="brand-mark__name">{APP_INFO.name}</span>
        <span className="brand-mark__product">{APP_INFO.portalName}</span>
      </span>
    </span>
  )
}
