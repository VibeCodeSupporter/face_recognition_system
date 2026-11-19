import { useEffect, useState } from 'react'
import { App as AntdApp, Form, Input, Modal, Select } from 'antd'
import userService from '../../services/userService.js'
import { getErrorMessage } from '../../services/apiClient.js'

export default function UserFormModal({ open, user, onClose, onSuccess }) {
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const [submitting, setSubmitting] = useState(false)

  const isEditing = Boolean(user?.id)

  useEffect(() => {
    if (open) {
      if (user) {
        form.setFieldsValue({
          user_code: user.user_code || '',
          full_name: user.full_name || '',
          email: user.email || '',
          phone: user.phone || '',
          department: user.department || '',
          role: user.role || '',
          status: user.status || 'active',
        })
      } else {
        form.resetFields()
        form.setFieldsValue({
          status: 'active',
        })
      }
    }
  }, [open, user, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)

      const payload = {
        user_code: values.user_code.trim(),
        full_name: values.full_name.trim(),
        email: values.email?.trim() || null,
        phone: values.phone?.trim() || null,
        department: values.department?.trim() || null,
        role: values.role?.trim() || null,
        status: values.status,
      }

      if (isEditing) {
        // Chỉ gửi những trường có thay đổi so với ban đầu
        const changedFields = {}
        for (const [key, value] of Object.entries(payload)) {
          if (value !== (user[key] ?? null)) {
            changedFields[key] = value
          }
        }

        if (Object.keys(changedFields).length === 0) {
          message.info('Không có thay đổi nào để lưu.')
          onClose()
          return
        }

        await userService.updateUser(user.id, changedFields)
        message.success('Cập nhật người dùng thành công!')
      } else {
        await userService.createUser(payload)
        message.success('Thêm người dùng mới thành công!')
      }

      onSuccess()
      onClose()
    } catch (error) {
      if (error?.errorFields) {
        return // Lỗi validate client form
      }
      message.error(getErrorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title={isEditing ? `Sửa thông tin: ${user.full_name}` : 'Thêm người dùng mới'}
      open={open}
      onCancel={onClose}
      onOk={handleSubmit}
      okText={isEditing ? 'Lưu thay đổi' : 'Thêm mới'}
      cancelText="Hủy"
      confirmLoading={submitting}
      destroyOnClose
      width={600}
    >
      <Form form={form} layout="vertical" requiredMark="optional" style={{ marginTop: 16 }}>
        <Form.Item
          name="user_code"
          label="Mã nhân viên"
          rules={[
            { required: true, message: 'Vui lòng nhập mã nhân viên!' },
            { max: 50, message: 'Tối đa 50 ký tự!' },
          ]}
        >
          <Input placeholder="Ví dụ: NV001, EMP-2024" />
        </Form.Item>

        <Form.Item
          name="full_name"
          label="Họ và tên"
          rules={[
            { required: true, message: 'Vui lòng nhập họ và tên!' },
            { max: 150, message: 'Tối đa 150 ký tự!' },
          ]}
        >
          <Input placeholder="Ví dụ: Nguyễn Văn A" />
        </Form.Item>

        <Form.Item
          name="email"
          label="Email"
          rules={[
            { type: 'email', message: 'Email không hợp lệ!' },
            { max: 150, message: 'Tối đa 150 ký tự!' },
          ]}
        >
          <Input placeholder="nguyenvana@company.com" />
        </Form.Item>

        <Form.Item
          name="phone"
          label="Số điện thoại"
          rules={[{ max: 20, message: 'Tối đa 20 ký tự!' }]}
        >
          <Input placeholder="0901234567" />
        </Form.Item>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <Form.Item
            name="department"
            label="Phòng ban"
            rules={[{ max: 100, message: 'Tối đa 100 ký tự!' }]}
          >
            <Input placeholder="Kỹ thuật / Nhân sự..." />
          </Form.Item>

          <Form.Item
            name="role"
            label="Chức danh"
            rules={[{ max: 50, message: 'Tối đa 50 ký tự!' }]}
          >
            <Input placeholder="Kỹ sư phần mềm / Quản lý..." />
          </Form.Item>
        </div>

        <Form.Item name="status" label="Trạng thái hoạt động" rules={[{ required: true }]}>
          <Select
            options={[
              { value: 'active', label: 'Hoạt động (Active)' },
              { value: 'inactive', label: 'Ngừng hoạt động (Inactive)' },
            ]}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}

