import { useEffect, useState } from 'react'
import {
  DeleteOutlined,
  DeploymentUnitOutlined,
  EditOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import {
  App as AntdApp,
  Button,
  Card,
  Input,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd'
import deviceService from '../../services/deviceService.js'
import { formatDateTimeVN, getErrorMessage } from '../../services/apiClient.js'
import DeviceDetailModal from './DeviceDetailModal.jsx'
import DeviceFormModal from './DeviceFormModal.jsx'
import DeviceTokenModal from './DeviceTokenModal.jsx'

const { Title, Text } = Typography

const STATUS_TAGS = {
  online: { label: 'Online', color: 'success' },
  offline: { label: 'Offline', color: 'default' },
  warning: { label: 'Cảnh báo', color: 'warning' },
}

export default function DevicesPage() {
  const { message } = AntdApp.useApp()

  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)

  // Filters & Pagination
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState('')
  const [deviceCodeFilter, setDeviceCodeFilter] = useState('')

  // Modals
  const [formModalOpen, setFormModalOpen] = useState(false)
  const [selectedDeviceForEdit, setSelectedDeviceForEdit] = useState(null)

  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [selectedDeviceForDetail, setSelectedDeviceForDetail] = useState(null)

  const [tokenModalOpen, setTokenModalOpen] = useState(false)
  const [newTokenData, setNewTokenData] = useState({ token: '', name: '' })

  const fetchDevices = async () => {
    setLoading(true)
    try {
      const params = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
      }
      if (statusFilter) params.status = statusFilter
      if (deviceCodeFilter.trim()) params.device_code = deviceCodeFilter.trim()

      const data = await deviceService.listDevices(params)
      setDevices(data.items || [])
      setTotal(data.total || (data.items || []).length)
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDevices()
  }, [page, pageSize, statusFilter, deviceCodeFilter])

  const handleDeleteDevice = async (id) => {
    try {
      await deviceService.deleteDevice(id)
      message.success('Đã xóa thiết bị thành công!')
      fetchDevices()
    } catch (error) {
      message.error(getErrorMessage(error))
    }
  }

  const handleDeviceCreated = (token, name) => {
    setNewTokenData({ token, name })
    setTokenModalOpen(true)
  }

  const columns = [
    {
      title: 'Thiết bị',
      key: 'device',
      width: 250,
      render: (_, record) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap' }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 8,
              backgroundColor: '#e0f2fe',
              color: '#0284c7',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 17,
              flexShrink: 0,
            }}
          >
            <DeploymentUnitOutlined />
          </div>
          <span style={{ fontWeight: 600, color: '#0f172a' }}>{record.name}</span>
        </div>
      ),
    },
    {
      title: 'Mã thiết bị',
      dataIndex: 'device_code',
      key: 'device_code',
      width: 140,
      render: (code) => (
        <Tag
          style={{
            backgroundColor: '#e0f2fe',
            color: '#0369a1',
            border: '1px solid #bae6fd',
            fontWeight: 600,
            whiteSpace: 'nowrap',
          }}
        >
          {code}
        </Tag>
      ),
    },
    {
      title: 'Vị trí lắp đặt',
      dataIndex: 'location',
      key: 'location',
      width: 180,
      render: (loc) => <span style={{ whiteSpace: 'nowrap' }}>{loc || '—'}</span>,
    },
    {
      title: 'Trạng thái',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (status) => {
        const conf = STATUS_TAGS[status] || { label: status, color: 'default' }
        return (
          <Tag color={conf.color} style={{ fontWeight: 500, whiteSpace: 'nowrap' }}>
            {conf.label}
          </Tag>
        )
      },
    },
    {
      title: 'Cấu hình nhận diện',
      key: 'settings',
      width: 240,
      render: (_, record) => (
        <div style={{ whiteSpace: 'nowrap' }}>
          <span>
            Ngưỡng: <strong>{record.settings?.threshold ?? '—'}%</strong> · Khóa:{' '}
            <strong>{record.settings?.doorDuration ?? '—'}s</strong>
          </span>
          <span style={{ color: '#64748b', marginLeft: 8, fontSize: 12 }}>
            (Liveness: {record.settings?.liveness ? 'Bật' : 'Tắt'})
          </span>
        </div>
      ),
    },
    {
      title: 'Lần hoạt động cuối',
      dataIndex: 'last_seen_at',
      key: 'last_seen_at',
      width: 175,
      render: (date) => <span style={{ whiteSpace: 'nowrap' }}>{formatDateTimeVN(date)}</span>,
    },
    {
      title: 'Thao tác',
      key: 'actions',
      align: 'right',
      width: 140,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small" style={{ whiteSpace: 'nowrap' }}>
          <Tooltip title="Xem chi tiết">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedDeviceForDetail(record)
                setDetailModalOpen(true)
              }}
            />
          </Tooltip>
          <Tooltip title="Sửa thiết bị">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedDeviceForEdit(record)
                setFormModalOpen(true)
              }}
            />
          </Tooltip>
          <Popconfirm
            title="Xác nhận xóa thiết bị?"
            description={`Bạn có chắc muốn xóa thiết bị "${record.name}"?`}
            onConfirm={() => handleDeleteDevice(record.id)}
            okText="Xóa"
            cancelText="Hủy"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="Xóa thiết bị">
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <div>
          <Title level={3} style={{ margin: 0 }}>
            Quản lý Thiết bị (Edge Devices)
          </Title>
          <Text type="secondary">
            Cấu hình các bộ điều khiển cửa, camera nhận diện và theo dõi kết nối thiết bị.
          </Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchDevices} loading={loading}>
            Tải lại
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setSelectedDeviceForEdit(null)
              setFormModalOpen(true)
            }}
          >
            Thêm thiết bị
          </Button>
        </Space>
      </div>

      <Card style={{ marginBottom: 16 }} size="small">
        <Space wrap size="middle">
          <Input
            placeholder="Lọc theo mã thiết bị..."
            prefix={<SearchOutlined />}
            value={deviceCodeFilter}
            onChange={(e) => {
              setDeviceCodeFilter(e.target.value)
              setPage(1)
            }}
            style={{ width: 240 }}
            allowClear
          />
          <Select
            placeholder="Trạng thái kết nối"
            value={statusFilter}
            onChange={(val) => {
              setStatusFilter(val)
              setPage(1)
            }}
            style={{ width: 180 }}
            options={[
              { value: '', label: 'Tất cả trạng thái' },
              { value: 'online', label: 'Online' },
              { value: 'offline', label: 'Offline' },
              { value: 'warning', label: 'Cảnh báo' },
            ]}
          />
          {(statusFilter || deviceCodeFilter) && (
            <Button
              type="link"
              onClick={() => {
                setStatusFilter('')
                setDeviceCodeFilter('')
                setPage(1)
              }}
            >
              Xóa lọc
            </Button>
          )}
        </Space>
      </Card>

      <Card styles={{ body: { padding: 0 } }} style={{ border: '1px solid #e0f2fe' }}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={devices}
          loading={loading}
          scroll={{ x: 1150 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100'],
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps)
            },
            showTotal: (tot) => `Tổng số ${tot} thiết bị`,
          }}
        />
      </Card>

      <DeviceFormModal
        open={formModalOpen}
        device={selectedDeviceForEdit}
        onClose={() => setFormModalOpen(false)}
        onSuccess={fetchDevices}
        onNewDeviceCreated={handleDeviceCreated}
      />

      <DeviceDetailModal
        open={detailModalOpen}
        device={selectedDeviceForDetail}
        onClose={() => setDetailModalOpen(false)}
      />

      <DeviceTokenModal
        open={tokenModalOpen}
        token={newTokenData.token}
        deviceName={newTokenData.name}
        onClose={() => setTokenModalOpen(false)}
      />
    </div>
  )
}

