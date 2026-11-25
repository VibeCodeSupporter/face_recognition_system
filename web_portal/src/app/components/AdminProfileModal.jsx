import { useEffect, useState } from 'react'
import {
  LockOutlined,
  SafetyCertificateOutlined,
  SaveOutlined,
  UserOutlined,
} from '@ant-design/icons'
import {
  App as AntdApp,
  Avatar,
  Button,
  Form,
  Input,
  Modal,
  Space,
  Tag,
  Typography,
} from 'antd'
import { useAuth } from '../providers/AuthProvider.jsx'
import { getErrorMessage } from '../services/apiClient.js'

const { Text } = Typography

export default function AdminProfileModal({ open, onClose }) {
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { admin, isSuperAdmin, updateProfile } = useAuth()
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        username: admin?.username || 'admin',
        full_name: admin?.full_name || 'Quản trị viên Hệ thống',
        role: isSuperAdmin
          ? 'Quản trị viên Cấp cao (Toàn quyền)'
          : 'Nhân viên Vận hành (Xem, Tìm kiếm & Thêm Embedding)',
        new_password: '',
        confirm_password: '',
      })
    }
  }, [open, admin, isSuperAdmin, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()

      if (values.new_password) {
        if (values.new_password.length < 6) {
          message.error('Mật khẩu mới phải có ít nhất 6 ký tự!')
          return
        }
        if (values.new_password !== values.confirm_password) {
          message.error('Mật khẩu xác nhận không khớp!')
          return
        }
      }

      setSubmitting(true)
      const payload = {
        full_name: values.full_name?.trim() || null,
        new_password: values.new_password?.trim() || undefined,
      }

      await updateProfile(payload)
      message.success('Cập nhật thông tin Quản trị viên thành công!')
      onClose()
    } catch (error) {
      if (error?.errorFields) return
      message.error(getErrorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <SafetyCertificateOutlined style={{ color: '#0284c7', fontSize: 20 }} />
          <span>Hồ sơ Quản trị viên</span>
        </div>
      }
      open={open}
      onCancel={onClose}
      onOk={handleSubmit}
      okText="Lưu thay đổi"
      cancelText="Đóng"
      confirmLoading={submitting}
      destroyOnClose
      width={520}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 10,
          margin: '16px 0 20px',
          padding: '16px',
          background: 'linear-gradient(135deg, #f0f9ff 0%, #fefce8 100%)',
          borderRadius: 12,
          border: '1px solid #bae6fd',
        }}
      >
        <Avatar
          size={64}
          style={{
            backgroundColor: '#0284c7',
            boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)',
            fontSize: 26,
            fontWeight: 700,
          }}
        >
          {(admin?.full_name || admin?.username || 'A').charAt(0).toUpperCase()}
        </Avatar>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#0f172a' }}>
            {admin?.full_name || 'Quản trị viên'}
          </div>
          <Text type="secondary" style={{ fontSize: 13 }}>
            Tài khoản: @{admin?.username || 'admin'}
          </Text>
        </div>
        <Tag color={isSuperAdmin ? 'gold' : 'blue'} style={{ fontWeight: 600, padding: '2px 10px', borderRadius: 12 }}>
          {isSuperAdmin
            ? 'Quản trị viên Cấp cao · Toàn quyền'
            : 'Vận hành · Xem, Tìm kiếm & Thêm Embedding'}
        </Tag>
        <div style={{ fontSize: 12, color: '#475569', textAlign: 'center', marginTop: 2 }}>
          {isSuperAdmin
            ? 'Quyền: Thêm/sửa/xóa người dùng, thiết bị, phiên đăng ký, vector khuôn mặt & xóa lịch sử truy cập.'
            : 'Quyền: Xem & tìm kiếm người dùng, thiết bị, phiên, lịch sử truy cập và thêm mới vector khuôn mặt.'}
        </div>
      </div>

      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="username" label="Tên đăng nhập (Username)">
          <Input prefix={<UserOutlined style={{ color: '#0284c7' }} />} disabled />
        </Form.Item>

        <Form.Item
          name="full_name"
          label="Họ và tên Quản trị viên"
          rules={[{ required: true, message: 'Vui lòng nhập họ và tên!' }]}
        >
          <Input placeholder="Ví dụ: Nguyễn Văn Quản Trị" />
        </Form.Item>

        <Form.Item
          name="new_password"
          label="Mật khẩu mới (Để trống nếu không đổi)"
          extra="Nếu muốn đổi mật khẩu đăng nhập, hãy nhập mật khẩu mới tại đây."
        >
          <Input.Password
            prefix={<LockOutlined style={{ color: '#eab308' }} />}
            placeholder="Nhập mật khẩu mới"
          />
        </Form.Item>

        <Form.Item
          name="confirm_password"
          label="Xác nhận mật khẩu mới"
          dependencies={['new_password']}
        >
          <Input.Password
            prefix={<LockOutlined style={{ color: '#eab308' }} />}
            placeholder="Nhập lại mật khẩu mới"
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}

