import { Typography } from 'antd'
import './AuthCard.css'

/**
 * Khung nội dung của một màn hình auth: tiêu đề + mô tả + vùng form + footer.
 * Dùng chung cho Login / Register / Forgot password để 3 page không lặp markup.
 *
 * @param {object} props
 * @param {React.ReactNode} props.title
 * @param {React.ReactNode} [props.description]
 * @param {React.ReactNode} props.children - form
 * @param {React.ReactNode} [props.footer] - link chuyển màn hình
 */
export default function AuthCard({ title, description, children, footer }) {
  return (
    <section className="auth-card">
      <header className="auth-card__header">
        <Typography.Title level={2} className="auth-card__title">
          {title}
        </Typography.Title>
        {description ? (
          <Typography.Paragraph className="auth-card__description">
            {description}
          </Typography.Paragraph>
        ) : null}
      </header>

      <div className="auth-card__body">{children}</div>

      {footer ? <footer className="auth-card__footer">{footer}</footer> : null}
    </section>
  )
}
