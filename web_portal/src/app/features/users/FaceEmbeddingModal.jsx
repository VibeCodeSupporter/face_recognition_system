import { useEffect, useState } from 'react'
import {
  CheckCircleOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  ExperimentOutlined,
  SaveOutlined,
} from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Spin,
  Tag,
  Typography,
} from 'antd'
import userService from '../../services/userService.js'
import { formatDateTimeVN, getErrorMessage } from '../../services/apiClient.js'

const { Text } = Typography

export default function FaceEmbeddingModal({ open, user, onClose, onSuccess }) {
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()

  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [embedding, setEmbedding] = useState(null)

  useEffect(() => {
    if (open && user?.id) {
      loadEmbedding()
    } else {
      setEmbedding(null)
      form.resetFields()
    }
  }, [open, user])

  const loadEmbedding = async () => {
    setLoading(true)
    try {
      const data = await userService.getFaceEmbedding(user.id)
      setEmbedding(data)
      if (data) {
        form.setFieldsValue({
          model_name: data.model_name || 'Facenet512',
          model_version: data.model_version || 'v1',
          dimension: data.dimension || (data.embedding_data ? data.embedding_data.length : 512),
          image_url: data.image_url || '',
          embedding_data: data.embedding_data ? JSON.stringify(data.embedding_data) : '',
        })
      } else {
        form.setFieldsValue({
          model_name: 'Facenet512',
          model_version: 'v1',
          dimension: 512,
          image_url: '',
          embedding_data: '',
        })
      }
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateSample = () => {
    const dim = form.getFieldValue('dimension') || 512
    const vector = Array.from({ length: dim }, () =>
      Number((Math.random() * 2 - 1).toFixed(6))
    )
    form.setFieldsValue({
      embedding_data: JSON.stringify(vector),
    })
    message.info(`Đã tạo vector mẫu gồm ${dim} chiều.`)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)

      let parsedVector
      try {
        parsedVector = JSON.parse(values.embedding_data)
      } catch {
        message.error('Vector phải là mảng JSON hợp lệ! (Ví dụ: [0.12, -0.45, ...])')
        setSubmitting(false)
        return
      }

      if (!Array.isArray(parsedVector)) {
        message.error('Vector phải là một mảng JSON các số.')
        setSubmitting(false)
        return
      }

      if (parsedVector.some((num) => typeof num !== 'number' || !Number.isFinite(num))) {
        message.error('Mọi phần tử trong vector phải là số thực hữu hạn.')
        setSubmitting(false)
        return
      }

      if (parsedVector.length !== values.dimension) {
        message.error(
          `Số phần tử trong vector (${parsedVector.length}) không khớp với số chiều khai báo (${values.dimension}).`
        )
        setSubmitting(false)
        return
      }

      const payload = {
        model_name: values.model_name.trim(),
        model_version: values.model_version.trim(),
        dimension: values.dimension,
        image_url: values.image_url?.trim() || null,
        embedding_data: parsedVector,
      }

      await userService.saveFaceEmbedding(user.id, payload)
      message.success('Đã lưu vector khuôn mặt vào cơ sở dữ liệu!')
      onSuccess?.()
      onClose()
    } catch (error) {
      if (error?.errorFields) return
      message.error(getErrorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    setSubmitting(true)
    try {
      await userService.deleteFaceEmbedding(user.id)
      message.success('Đã xóa vector khuôn mặt.')
      setEmbedding(null)
      form.setFieldsValue({ embedding_data: '' })
      onSuccess?.()
      onClose()
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>Vector khuôn mặt</span>
          {user && <Tag color="blue">{user.full_name} · {user.user_code}</Tag>}
        </div>
      }
      open={open}
      onCancel={onClose}
      footer={[
        embedding ? (
          <Popconfirm
            key="delete"
            title="Xóa vector khuôn mặt?"
            description="Thao tác này sẽ xóa vector đã lưu. Người dùng sẽ không thể nhận diện tại cửa cho đến khi đăng ký lại."
            onConfirm={handleDelete}
            okText="Xóa"
            cancelText="Hủy"
            okButtonProps={{ danger: true, loading: submitting }}
          >
            <Button danger icon={<DeleteOutlined />} style={{ float: 'left' }}>
              Xóa vector
            </Button>
          </Popconfirm>
        ) : null,
        <Button key="cancel" onClick={onClose}>
          Đóng
        </Button>,
        <Button
          key="submit"
          type="primary"
          icon={<SaveOutlined />}
          loading={submitting}
          onClick={handleSubmit}
        >
          Lưu vector
        </Button>,
      ]}
      width={720}
      destroyOnClose
    >
      <Spin spinning={loading}>
        <div style={{ marginTop: 12, marginBottom: 16 }}>
          {embedding ? (
            <Alert
              type="success"
              showIcon
              icon={<CheckCircleOutlined />}
              title="Người dùng đã có vector khuôn mặt"
              description={
                <div style={{ fontSize: 13, marginTop: 4 }}>
                  <div>
                    Model: <strong>{embedding.model_name}</strong> (v{embedding.model_version}) · Số chiều: <strong>{embedding.dimension}</strong>
                  </div>
                  <div>Cập nhật: {formatDateTimeVN(embedding.updated_at || embedding.created_at)}</div>
                </div>
              }
            />
          ) : (
            <Alert
              type="warning"
              showIcon
              icon={<ExclamationCircleOutlined />}
              title="Chưa có dữ liệu vector khuôn mặt"
              description="Bạn có thể nhập vector từ model AI thực tế hoặc tạo mẫu thử nghiệm để kiểm tra."
            />
          )}
        </div>

        <Form form={form} layout="vertical" requiredMark="optional">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            <Form.Item
              name="model_name"
              label="Tên model"
              rules={[{ required: true, message: 'Nhập tên model!' }]}
            >
              <Input placeholder="Facenet512" />
            </Form.Item>

            <Form.Item
              name="model_version"
              label="Phiên bản"
              rules={[{ required: true, message: 'Nhập phiên bản!' }]}
            >
              <Input placeholder="v1" />
            </Form.Item>

            <Form.Item
              name="dimension"
              label="Số chiều"
              rules={[{ required: true, message: 'Nhập số chiều!' }]}
            >
              <InputNumber min={1} max={4096} style={{ width: '100%' }} />
            </Form.Item>
          </div>

          <Form.Item name="image_url" label="URL ảnh khuôn mặt (tùy chọn)">
            <Input placeholder="https://example.com/face.jpg" />
          </Form.Item>

          <Form.Item
            name="embedding_data"
            label={
              <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                <span>Dữ liệu vector (Mảng JSON)</span>
                <Button
                  size="small"
                  type="dashed"
                  icon={<ExperimentOutlined />}
                  onClick={handleGenerateSample}
                >
                  Tạo vector mẫu ngẫu nhiên
                </Button>
              </div>
            }
            rules={[{ required: true, message: 'Vui lòng nhập vector khuôn mặt!' }]}
            extra="Định dạng: Mảng các số thực JSON, ví dụ: [0.012, -0.054, 0.129, ...]"
          >
            <Input.TextArea
              rows={6}
              placeholder="[0.012, -0.054, ...]"
              style={{ fontFamily: 'monospace', fontSize: 12 }}
            />
          </Form.Item>
        </Form>
      </Spin>
    </Modal>
  )
}

