import { useEffect, useState } from 'react'
import { App as AntdApp, DatePicker, Form, Modal, Select } from 'antd'
import dayjs from 'dayjs'
import sessionService from '../../services/sessionService.js'
import { getErrorMessage } from '../../services/apiClient.js'

const normalizeText = (str) =>
  (str || '')
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()

export default function SessionCreateModal({ open, users, devices, onClose, onSuccess }) {
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const [submitting, setSubmitting] = useState(false)

  // Chỉ lấy những user đang active
  const activeUsers = (users || []).filter((u) => u.status === 'active')

  useEffect(() => {
    if (open) {
      form.resetFields()
      // Mặc định hết hạn sau 30 phút
      form.setFieldsValue({
        expires_at: dayjs().add(30, 'minute'),
      })
    }
  }, [open, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()

      if (values.expires_at) {
        const expiresTime = values.expires_at.valueOf()
        const oneMinuteLater = Date.now() + 60000
        if (expiresTime <= oneMinuteLater) {
          message.error('Thời hạn hết hạn của phiên phải cách thời điểm hiện tại hơn 1 phút!')
          return
        }
      }

      setSubmitting(true)

      const payload = {
        user_id: values.user_id,
        device_id: values.device_id,
        expires_at: values.expires_at ? values.expires_at.toISOString() : undefined,
      }

      await sessionService.createSession(payload)
      message.success('Tạo phiên đăng ký khuôn mặt thành công!')
      onSuccess()
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
      title="Tạo phiên đăng ký khuôn mặt mới"
      open={open}
      onCancel={onClose}
      onOk={handleSubmit}
      okText="Tạo phiên"
      cancelText="Hủy"
      confirmLoading={submitting}
      destroyOnClose
      width={560}
    >
      <Form form={form} layout="vertical" requiredMark="optional" style={{ marginTop: 16 }}>
        <Form.Item
          name="user_id"
          label="Người dùng cần đăng ký"
          rules={[{ required: true, message: 'Vui lòng chọn người dùng!' }]}
          extra="Chỉ những người dùng đang có trạng thái Hoạt động (Active) mới được phép tạo phiên."
        >
          <Select
            showSearch
            placeholder="Nhập tên hoặc mã nhân viên..."
            filterOption={(input, option) => {
              if (!input) return true
              const q = normalizeText(input)
              const label = normalizeText(option?.label)
              const code = normalizeText(option?.userCode)
              const name = normalizeText(option?.fullName)
              return label.includes(q) || code.includes(q) || name.includes(q)
            }}
            options={activeUsers.map((u) => ({
              value: u.id,
              label: `[${u.user_code}] ${u.full_name}${u.department ? ` · ${u.department}` : ''}`,
              fullName: u.full_name,
              userCode: u.user_code,
            }))}
          />
        </Form.Item>

        <Form.Item
          name="device_id"
          label="Thiết bị thực hiện đăng ký"
          rules={[{ required: true, message: 'Vui lòng chọn thiết bị!' }]}
        >
          <Select
            showSearch
            placeholder="Chọn thiết bị tại cửa..."
            filterOption={(input, option) => {
              if (!input) return true
              const q = normalizeText(input)
              const label = normalizeText(option?.label)
              return label.includes(q)
            }}
            options={(devices || []).map((d) => ({
              value: d.id,
              label: `[${d.device_code}] ${d.name}${d.location ? ` · ${d.location}` : ''}`,
            }))}
          />
        </Form.Item>

        <Form.Item
          name="expires_at"
          label="Thời hạn hết hạn phiên"
          extra="Sau thời gian này, thiết bị sẽ tự động hủy phiên nếu chưa hoàn tất đăng ký."
        >
          <DatePicker
            showTime
            format="DD/MM/YYYY HH:mm:ss"
            style={{ width: '100%' }}
            disabledDate={(current) => current && current < dayjs().startOf('day')}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}

