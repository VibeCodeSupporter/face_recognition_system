import { Descriptions, Modal, Tag } from 'antd'
import { formatDateTimeVN } from '../../services/apiClient.js'

const STATUS_CONFIG = {
  online: { label: 'Online', color: 'success' },
  offline: { label: 'Offline', color: 'default' },
  warning: { label: 'Cảnh báo', color: 'warning' },
}

export default function DeviceDetailModal({ open, device, onClose }) {
  if (!device) return null

  const statusInfo = STATUS_CONFIG[device.status] || {
    label: device.status || '—',
    color: 'default',
  }

  return (
    <Modal
      title="Chi tiết Thiết bị Kiểm soát cửa"
      open={open}
      onCancel={onClose}
      footer={null}
      width={650}
    >
      <Descriptions bordered column={1} size="small" style={{ marginTop: 16 }}>
        <Descriptions.Item label="ID (UUID)">
          <code style={{ fontSize: 12 }}>{device.id}</code>
        </Descriptions.Item>
        <Descriptions.Item label="Mã thiết bị">
          <strong>{device.device_code}</strong>
        </Descriptions.Item>
        <Descriptions.Item label="Tên thiết bị">{device.name}</Descriptions.Item>
        <Descriptions.Item label="Vị trí lắp đặt">{device.location || '—'}</Descriptions.Item>
        <Descriptions.Item label="Trạng thái">
          <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Cấu hình nhận diện">
          <div style={{ fontSize: 13 }}>
            <div>
              Ngưỡng tin cậy (Threshold): <strong>{device.settings?.threshold ?? '—'}%</strong>
            </div>
            <div>
              Thời gian mở cửa: <strong>{device.settings?.doorDuration ?? '—'} giây</strong>
            </div>
            <div>
              Kiểm tra Liveness:{' '}
              <Tag color={device.settings?.liveness ? 'blue' : 'default'} style={{ marginLeft: 4 }}>
                {device.settings?.liveness ? 'BẬT' : 'TẮT'}
              </Tag>
            </div>
          </div>
        </Descriptions.Item>
        <Descriptions.Item label="Lần hoạt động cuối">
          {formatDateTimeVN(device.last_seen_at)}
        </Descriptions.Item>
        <Descriptions.Item label="Ngày tạo">
          {formatDateTimeVN(device.created_at)}
        </Descriptions.Item>
      </Descriptions>
    </Modal>
  )
}

