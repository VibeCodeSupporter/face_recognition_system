import { useEffect, useState } from 'react'
import {
  App as AntdApp,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Slider,
  Switch,
} from 'antd'
import deviceService from '../../services/deviceService.js'
import { getErrorMessage } from '../../services/apiClient.js'

export default function DeviceFormModal({ open, device, onClose, onSuccess, onNewDeviceCreated }) {
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const [submitting, setSubmitting] = useState(false)

  const isEditing = Boolean(device?.id)

  useEffect(() => {
    if (open) {
      if (device) {
        form.setFieldsValue({
          device_code: device.device_code || '',
          name: device.name || '',
          location: device.location || '',
          status: device.status || 'offline',
          threshold: device.settings?.threshold ?? 80,
          doorDuration: device.settings?.doorDuration ?? 3,
          liveness: device.settings?.liveness ?? true,
        })
      } else {
        form.resetFields()
        form.setFieldsValue({
          status: 'offline',
          threshold: 80,
          doorDuration: 3,
          liveness: true,
        })
      }
    }
  }, [open, device, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)

      const payload = {
        device_code: values.device_code.trim(),
        name: values.name.trim(),
        location: values.location?.trim() || null,
        status: values.status,
        settings: {
          threshold: values.threshold,
          doorDuration: values.doorDuration,
          liveness: values.liveness,
        },
      }

      if (isEditing) {
        // Dirty check
        const patchData = {}
        if (payload.device_code !== device.device_code) patchData.device_code = payload.device_code
        if (payload.name !== device.name) patchData.name = payload.name
        if (payload.location !== (device.location ?? null)) patchData.location = payload.location
        if (payload.status !== device.status) patchData.status = payload.status

        const prevSettings = device.settings || {}
        if (
          payload.settings.threshold !== prevSettings.threshold ||
          payload.settings.doorDuration !== prevSettings.doorDuration ||
          payload.settings.liveness !== prevSettings.liveness
        ) {
          patchData.settings = payload.settings
        }

        if (Object.keys(patchData).length === 0) {
          message.info('Không có thay đổi nào để lưu.')
          onClose()
          return
        }

        await deviceService.updateDevice(device.id, patchData)
        message.success('Cập nhật thiết bị thành công!')
        onSuccess()
        onClose()
      } else {
        const createdData = await deviceService.createDevice(payload)
        message.success('Thêm thiết bị mới thành công!')
        onSuccess()
        onClose()

        // Nếu backend trả về token thiết bị một lần, báo cho component cha hiển thị
        if (createdData?.device_token) {
          onNewDeviceCreated?.(createdData.device_token, createdData.name || payload.name)
        }
      }
    } catch (error) {
      if (error?.errorFields) return
      message.error(getErrorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title={isEditing ? `Sửa thiết bị: ${device.name}` : 'Thêm thiết bị cửa mới'}
      open={open}
      onCancel={onClose}
      onOk={handleSubmit}
      okText={isEditing ? 'Lưu thay đổi' : 'Thêm thiết bị'}
      cancelText="Hủy"
      confirmLoading={submitting}
      destroyOnClose
      width={640}
    >
      <Form form={form} layout="vertical" requiredMark="optional" style={{ marginTop: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <Form.Item
            name="device_code"
            label="Mã thiết bị"
            rules={[
              { required: true, message: 'Nhập mã thiết bị!' },
              { max: 50, message: 'Tối đa 50 ký tự!' },
            ]}
          >
            <Input placeholder="Ví dụ: DOOR_MAIN_01" />
          </Form.Item>

          <Form.Item
            name="name"
            label="Tên thiết bị"
            rules={[
              { required: true, message: 'Nhập tên thiết bị!' },
              { max: 100, message: 'Tối đa 100 ký tự!' },
            ]}
          >
            <Input placeholder="Cửa chính Tầng 1" />
          </Form.Item>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Form.Item
            name="location"
            label="Vị trí lắp đặt"
            rules={[{ max: 200, message: 'Tối đa 200 ký tự!' }]}
          >
            <Input placeholder="Tòa nhà A, sảnh trước..." />
          </Form.Item>

          <Form.Item name="status" label="Trạng thái" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'online', label: 'Online' },
                { value: 'offline', label: 'Offline' },
                { value: 'warning', label: 'Cảnh báo' },
              ]}
            />
          </Form.Item>
        </div>

        <Card title="Cấu hình nhận diện & kiểm soát cửa" size="small" style={{ marginTop: 8 }}>
          <Form.Item
            name="threshold"
            label="Ngưỡng tin cậy nhận diện (%)"
            rules={[{ required: true, message: 'Nhập ngưỡng nhận diện!' }]}
            extra="Độ tương đồng tối thiểu để nhận diện hợp lệ và mở cửa (mặc định: 80%)"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <Slider
                min={0}
                max={100}
                style={{ flex: 1 }}
                value={form.getFieldValue('threshold')}
                onChange={(val) => form.setFieldsValue({ threshold: val })}
              />
              <InputNumber min={0} max={100} style={{ width: 80 }} />
            </div>
          </Form.Item>

          <Form.Item
            name="doorDuration"
            label="Thời gian giữ mở cửa (giây)"
            rules={[{ required: true, message: 'Nhập thời gian mở cửa!' }]}
            extra="Thời gian chốt khóa mở sau khi nhận diện thành công (1 - 60 giây)"
          >
            <InputNumber min={1} max={60} style={{ width: 140 }} />
          </Form.Item>

          <Form.Item
            name="liveness"
            label="Kiểm tra khuôn mặt thật (Liveness Detection)"
            valuePropName="checked"
            extra="Phát hiện và chống gian lận ảnh chụp, video phát lại hoặc mặt nạ"
          >
            <Switch checkedChildren="Bật" unCheckedChildren="Tắt" />
          </Form.Item>
        </Card>
      </Form>
    </Modal>
  )
}

