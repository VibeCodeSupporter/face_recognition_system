import { useState } from 'react'
import { CheckOutlined, CopyOutlined, KeyOutlined, WarningOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Modal, Typography } from 'antd'

const { Paragraph, Text } = Typography

export default function DeviceTokenModal({ open, token, deviceName, onClose }) {
  const { message } = AntdApp.useApp()
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(token)
      setCopied(true)
      message.success('Đã sao chép token thiết bị vào clipboard!')
      setTimeout(() => setCopied(false), 3000)
    } catch (_) {
      message.error('Không thể sao chép tự động. Vui lòng bôi đen và sao chép thủ công.')
    }
  }

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#fa8c16' }}>
          <KeyOutlined />
          <span>Token xác thực cho thiết bị mới: {deviceName}</span>
        </div>
      }
      open={open}
      onCancel={onClose}
      footer={[
        <Button
          key="copy"
          type="primary"
          icon={copied ? <CheckOutlined /> : <CopyOutlined />}
          onClick={handleCopy}
          style={{ backgroundColor: copied ? '#52c41a' : undefined }}
        >
          {copied ? 'Đã sao chép' : 'Sao chép Token'}
        </Button>,
        <Button key="close" onClick={onClose}>
          Tôi đã lưu token, Đóng
        </Button>,
      ]}
      width={600}
      closable={false}
      maskClosable={false}
    >
      <Alert
        type="warning"
        showIcon
        icon={<WarningOutlined />}
        title="Lưu ý quan trọng về bảo mật"
        description="Token này CHỈ hiển thị duy nhất một lần tại thời điểm tạo thiết bị. Bạn hãy sao chép và cấu hình vào thiết bị (Edge Device) ngay trước khi đóng cửa sổ này."
        style={{ marginTop: 12, marginBottom: 16 }}
      />

      <div style={{ background: '#f5f5f5', padding: '16px', borderRadius: 8 }}>
        <Text type="secondary" style={{ fontSize: 13, display: 'block', marginBottom: 8 }}>
          Mã token thiết bị:
        </Text>
        <Paragraph
          copyable={{ text: token }}
          style={{
            fontFamily: 'monospace',
            fontSize: 14,
            fontWeight: 600,
            wordBreak: 'break-all',
            margin: 0,
            color: '#1677ff',
          }}
        >
          {token}
        </Paragraph>
      </div>
    </Modal>
  )
}

