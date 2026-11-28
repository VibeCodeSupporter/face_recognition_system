import { useEffect, useState } from 'react'
import {
  CheckCircleOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  ExperimentOutlined,
  PictureOutlined,
  SaveOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Card,
  Collapse,
  Descriptions,
  Form,
  Image,
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
import { useAuth } from '../../providers/AuthProvider.jsx'

const { Text } = Typography

export default function FaceEmbeddingModal({ open, user, onClose, onSuccess }) {
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { hasPermission } = useAuth()

  const canAddNew = hasPermission('embeddings:create')
  const canEditExisting = hasPermission('embeddings:update')
  const canDeleteExisting = hasPermission('embeddings:delete')

  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [embedding, setEmbedding] = useState(null)

  const canSave = embedding ? canEditExisting : canAddNew

  useEffect(() => {
    if (open && user?.id) {
      loadEmbedding()
    } else {
      setEmbedding(null)
      form.resetFields()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, user])

  const loadEmbedding = async () => {
    setLoading(true)
    try {
      const data = await userService.getFaceEmbedding(user.id)
      setEmbedding(data)
      if (data) {
        form.setFieldsValue({
          model_name: data.model_name || 'GhostFaceNet',
          model_version: data.model_version || '1.3',
          dimension: data.dimension || (data.embedding_data ? data.embedding_data.length : 512),
          image_url: data.image_url || '',
          embedding_data: data.embedding_data ? JSON.stringify(data.embedding_data) : '',
        })
      } else {
        form.setFieldsValue({
          model_name: 'GhostFaceNet',
          model_version: '1.3',
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
      message.success('Đã lưu dữ liệu khuôn mặt vào cơ sở dữ liệu!')
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
      message.success('Đã xóa dữ liệu khuôn mặt.')
      setEmbedding(null)
      form.setFieldsValue({ image_url: '', embedding_data: '' })
      onSuccess?.()
      onClose()
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  const technicalFormFields = (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
        <Form.Item
          name="model_name"
          label="Tên model"
          rules={[{ required: true, message: 'Nhập tên model!' }]}
        >
          <Input placeholder="GhostFaceNet" />
        </Form.Item>

        <Form.Item
          name="model_version"
          label="Phiên bản"
          rules={[{ required: true, message: 'Nhập phiên bản!' }]}
        >
          <Input placeholder="1.3" />
        </Form.Item>

        <Form.Item
          name="dimension"
          label="Số chiều"
          rules={[{ required: true, message: 'Nhập số chiều!' }]}
        >
          <InputNumber min={1} max={4096} style={{ width: '100%' }} />
        </Form.Item>
      </div>

      <Form.Item name="image_url" label="URL hoặc Base64 ảnh khuôn mặt (tùy chọn)">
        <Input placeholder="https://example.com/face.jpg hoặc data:image/jpeg;base64,..." />
      </Form.Item>

      <Form.Item
        name="embedding_data"
        label={
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
            <span>Dữ liệu vector (Mảng JSON)</span>
            {canSave && (
              <Button
                size="small"
                type="dashed"
                icon={<ExperimentOutlined />}
                onClick={handleGenerateSample}
              >
                Tạo vector mẫu ngẫu nhiên
              </Button>
            )}
          </div>
        }
        rules={[{ required: true, message: 'Vui lòng nhập vector khuôn mặt!' }]}
        extra="Định dạng: Mảng các số thực JSON, ví dụ: [0.012, -0.054, 0.129, ...]"
      >
        <Input.TextArea
          rows={5}
          placeholder="[0.012, -0.054, ...]"
          style={{ fontFamily: 'monospace', fontSize: 12 }}
        />
      </Form.Item>
    </>
  )

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>Hồ sơ Khuôn mặt</span>
          {user && <Tag color="blue">{user.full_name} · {user.user_code}</Tag>}
        </div>
      }
      open={open}
      onCancel={onClose}
      footer={[
        embedding && canDeleteExisting ? (
          <Popconfirm
            key="delete"
            title="Xóa dữ liệu khuôn mặt?"
            description="Thao tác này sẽ xóa ảnh và vector đã lưu. Người dùng sẽ không thể nhận diện tại cửa cho đến khi đăng ký lại."
            onConfirm={handleDelete}
            okText="Xóa"
            cancelText="Hủy"
            okButtonProps={{ danger: true, loading: submitting }}
          >
            <Button danger icon={<DeleteOutlined />} style={{ float: 'left' }}>
              Xóa dữ liệu
            </Button>
          </Popconfirm>
        ) : null,
        <Button key="cancel" onClick={onClose}>
          Đóng
        </Button>,
        canSave ? (
          <Button
            key="submit"
            type="primary"
            icon={<SaveOutlined />}
            loading={submitting}
            onClick={handleSubmit}
          >
            Lưu thay đổi
          </Button>
        ) : null,
      ]}
      width={660}
      destroyOnClose
    >
      <Spin spinning={loading}>
        <div style={{ marginTop: 12, marginBottom: 16 }}>
          {embedding ? (
            <Alert
              type="success"
              showIcon
              icon={<CheckCircleOutlined />}
              title="Đã đăng ký khuôn mặt trong hệ thống"
              description={
                !canEditExisting ? (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Tài khoản vận hành chỉ có quyền xem dữ liệu đã đăng ký, không được ghi đè hoặc xóa.
                  </Text>
                ) : null
              }
            />
          ) : (
            <Alert
              type="warning"
              showIcon
              icon={<ExclamationCircleOutlined />}
              title="Chưa có dữ liệu khuôn mặt"
              description="Người dùng này chưa đăng ký khuôn mặt tại thiết bị. Bạn có thể nhập vector thủ công bên dưới nếu cần."
            />
          )}
        </div>

        <Form form={form} layout="vertical" requiredMark="optional" disabled={!canSave}>
          {!loading && (
            <>
              <Card
                size="small"
                style={{
                  marginBottom: 12,
                  background: '#f8fafc',
                  borderColor: '#e2e8f0',
                  borderRadius: 12,
                }}
              >
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '170px 1fr',
                    gap: 20,
                    alignItems: 'center',
                  }}
                >
                  {/* Cột trái: Ảnh khuôn mặt */}
                  <div
                    style={{
                      width: 170,
                      height: 170,
                      borderRadius: 12,
                      border: '1px solid #bae6fd',
                      background: '#ffffff',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      overflow: 'hidden',
                    }}
                  >
                    {embedding?.image_url ? (
                      <Image
                        src={embedding.image_url}
                        alt="Ảnh khuôn mặt"
                        width={170}
                        height={170}
                        style={{ objectFit: 'cover' }}
                      />
                    ) : (
                      <div style={{ textAlign: 'center', color: '#94a3b8', padding: 12 }}>
                        <PictureOutlined style={{ fontSize: 36, marginBottom: 8 }} />
                        <div style={{ fontSize: 12 }}>
                          {embedding ? 'Chưa có ảnh xem trước' : 'Chưa có ảnh khuôn mặt'}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Cột phải: Thông tin tóm tắt gọn gàng */}
                  {embedding ? (
                    <Descriptions bordered column={1} size="small">
                      <Descriptions.Item label="Trạng thái">
                        <Tag color="success" style={{ margin: 0 }}>Đã kích hoạt</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="Model AI">
                        <strong>{embedding.model_name}</strong> (v{embedding.model_version})
                      </Descriptions.Item>
                      <Descriptions.Item label="Kích thước vector">
                        {embedding.dimension} chiều
                      </Descriptions.Item>
                      <Descriptions.Item label="Cập nhật lúc">
                        {formatDateTimeVN(embedding.updated_at || embedding.created_at)}
                      </Descriptions.Item>
                    </Descriptions>
                  ) : (
                    <Descriptions bordered column={1} size="small">
                      <Descriptions.Item label="Trạng thái">
                        <Tag color="warning" style={{ margin: 0 }}>Chưa đăng ký</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="Nhân viên">
                        <strong>{user?.full_name || '—'}</strong> ({user?.user_code || '—'})
                      </Descriptions.Item>
                      <Descriptions.Item label="Cách đăng ký">
                        Tạo phiên đăng ký và quét khuôn mặt trên thiết bị điểm danh.
                      </Descriptions.Item>
                    </Descriptions>
                  )}
                </div>
              </Card>

              {/* Ẩn các trường kỹ thuật (vector JSON & chuỗi Base64) vào mục mở rộng */}
              {canSave && (
                <Collapse
                  ghost
                  size="small"
                  items={[
                    {
                      key: 'technical',
                      label: (
                        <Text type="secondary" style={{ fontSize: 13 }}>
                          <SettingOutlined style={{ marginRight: 6 }} />
                          {embedding
                            ? 'Chỉnh sửa thông số & dữ liệu vector nâng cao'
                            : 'Nhập thủ công thông số & dữ liệu vector (Nâng cao)'}
                        </Text>
                      ),
                      children: technicalFormFields,
                    },
                  ]}
                />
              )}
            </>
          )}
        </Form>
      </Spin>
    </Modal>
  )
}
