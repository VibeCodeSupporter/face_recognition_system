import {
  HistoryOutlined,
  SafetyCertificateOutlined,
  SyncOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { Typography } from 'antd'
import BrandMark from '../../../components/BrandMark.jsx'
import { APP_INFO } from '../../../constants/appInfo.js'
import { AUTH_BRAND_CONTENT } from '../constants/authContent.js'
import './AuthBrandPanel.css'

/** Map iconKey (trong authContent) → icon component. */
const FEATURE_ICONS = {
  users: <TeamOutlined />,
  history: <HistoryOutlined />,
  devices: <SyncOutlined />,
  security: <SafetyCertificateOutlined />,
}

/**
 * Cột thương hiệu của vùng public: giới thiệu sản phẩm + các nhóm chức năng
 * chính của portal (người dùng/khuôn mặt, lịch sử ra vào, thiết bị, phân quyền).
 */
export default function AuthBrandPanel() {
  return (
    <div className="auth-brand">
      <div className="auth-brand__top">
        <BrandMark tone="light" />
      </div>

      <div className="auth-brand__body">
        <Typography.Title level={1} className="auth-brand__headline">
          {APP_INFO.headline}
        </Typography.Title>
        <Typography.Paragraph className="auth-brand__description">
          {APP_INFO.description}
        </Typography.Paragraph>

        <ul className="auth-brand__features">
          {AUTH_BRAND_CONTENT.features.map((feature) => (
            <li key={feature.key} className="auth-brand__feature">
              <span className="auth-brand__feature-icon" aria-hidden="true">
                {FEATURE_ICONS[feature.iconKey]}
              </span>
              <span className="auth-brand__feature-text">
                <span className="auth-brand__feature-title">{feature.title}</span>
                <span className="auth-brand__feature-description">{feature.description}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      <p className="auth-brand__footer">{AUTH_BRAND_CONTENT.footerNote}</p>
    </div>
  )
}
