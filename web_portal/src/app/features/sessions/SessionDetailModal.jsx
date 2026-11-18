import { Descriptions, Modal, Tag } from 'antd'
import { formatDateTimeVN } from '../../services/apiClient.js'

const STATUS_CONFIG = {
  pending: { label: 'Chờ đăng ký', color: 'warning' },
  completed: { label: 'Hoàn tất', color: 'success' },
  cancelled: { label: 'Đã hủy', color: 'default' },
  expired: { label: 'Hết hạn', color: 'error' },
  failed: { label: 'Thất bại', color: 'magenta' },
}

export default function SessionDetailModal({ open, session, users = [], devices = [], onClose }) {
  if (!session) return null

  const user = users.find((u) => u.id === session.user_id)
  const device = devices.find((d) => d.id === session.device_id)

  const statusInfo = STATUS_CONFIG[session.status] || {
    label: session.status || '—',
    color: 'default',
  }

  return (
    <Modal
      title="Chi tiết Phiên Đăng ký Khuôn mặt"
      open={open}
      onCancel={onClose}
      footer={null}
      width={650}
    >
      <Descriptions bordered column={1} size="small" style={{ marginTop: 16 }}>
        <Descriptions.Item label="ID Phiên (UUID)">
          <code style={{ fontSize: 12 }}>{session.id}</code>
        </Descriptions.Item>
        <Descriptions.Item label="Người dùng">
          {user ? (
            <span>
              <strong>{user.full_name}</strong> · Mã: {user.user_code}
            </span>
          ) : (
            session.user_id
          )}
        </Descriptions.Item>
        <Descriptions.Item label="Thiết bị">
          {device ? (
            <span>
              <strong>{device.name}</strong> · Mã: {device.device_code}
            </span>
          ) : (
            session.device_id
          )}
        </Descriptions.Item>
        <Descriptions.Item label="Trạng thái">
          <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Thời điểm tạo">
          {formatDateTimeVN(session.created_at)}
        </Descriptions.Item>
        <Descriptions.Item label="Thời hạn hết hạn">
          {formatDateTimeVN(session.expires_at)}
        </Descriptions.Item>
        <Descriptions.Item label="Thời điểm hoàn tất">
          {formatDateTimeVN(session.completed_at)}
        </Descriptions.Item>
      </Descriptions>
    </Modal>
  )
}

