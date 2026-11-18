import { Descriptions, Modal, Tag } from 'antd'
import { formatDateTimeVN } from '../../services/apiClient.js'

export default function UserDetailModal({ open, user, onClose }) {
  if (!user) return null

  return (
    <Modal
      title="Chi tiết Người dùng"
      open={open}
      onCancel={onClose}
      footer={null}
      width={650}
    >
      <Descriptions bordered column={1} size="small" style={{ marginTop: 16 }}>
        <Descriptions.Item label="ID (UUID)">
          <code style={{ fontSize: 12 }}>{user.id}</code>
        </Descriptions.Item>
        <Descriptions.Item label="Mã nhân viên">
          <strong>{user.user_code}</strong>
        </Descriptions.Item>
        <Descriptions.Item label="Họ và tên">{user.full_name}</Descriptions.Item>
        <Descriptions.Item label="Email">{user.email || '—'}</Descriptions.Item>
        <Descriptions.Item label="Số điện thoại">{user.phone || '—'}</Descriptions.Item>
        <Descriptions.Item label="Phòng ban">{user.department || '—'}</Descriptions.Item>
        <Descriptions.Item label="Chức danh">{user.role || '—'}</Descriptions.Item>
        <Descriptions.Item label="Trạng thái">
          <Tag color={user.status === 'active' ? 'success' : 'default'}>
            {user.status === 'active' ? 'Hoạt động' : 'Ngừng hoạt động'}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Ngày tạo">
          {formatDateTimeVN(user.created_at)}
        </Descriptions.Item>
        <Descriptions.Item label="Cập nhật gần nhất">
          {formatDateTimeVN(user.updated_at)}
        </Descriptions.Item>
      </Descriptions>
    </Modal>
  )
}

