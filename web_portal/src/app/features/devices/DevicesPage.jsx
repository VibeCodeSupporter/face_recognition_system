import { useEffect, useMemo, useState } from 'react'
import {
  ClearOutlined,
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
import { getErrorMessage } from '../../services/apiClient.js'
import { useAuth } from '../../providers/AuthProvider.jsx'
import DeviceDetailModal from './DeviceDetailModal.jsx'
import DeviceFormModal from './DeviceFormModal.jsx'
import DeviceTokenModal from './DeviceTokenModal.jsx'

const { Title, Text } = Typography

const normalizeText = (str) =>
  (str || '')
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()

const STATUS_TAGS = {
  online: { label: 'Online', color: 'success' },
  offline: { label: 'Offline', color: 'default' },
  warning: { label: 'Cảnh báo', color: 'warning' },
}

function renderCompactDateTime(value) {
  if (!value) return <Text type="secondary">—</Text>
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return <Text type="secondary">—</Text>
  const dateText = new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', year: '2-digit' }).format(date)
  const timeText = new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit' }).format(date)
  return <span style={{ display: 'inline-flex', flexDirection: 'column', lineHeight: 1.35, whiteSpace: 'nowrap' }}><span>{dateText}</span><Text type="secondary" style={{ fontSize: 12 }}>{timeText}</Text></span>
}

export default function DevicesPage() {
  const { message } = AntdApp.useApp()
  const { hasPermission } = useAuth()
  const canCreateDevice = hasPermission('devices:create')
  const canUpdateDevice = hasPermission('devices:update')
  const canDeleteDevice = hasPermission('devices:delete')

  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(false)

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
      const items = await deviceService.listAllDevices()
      setDevices(items || [])
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDevices()
  }, [])

  const filteredDevices = useMemo(() => {
    const q = normalizeText(deviceCodeFilter)
    return devices.filter((d) => {
      if (statusFilter && d.status !== statusFilter) return false
      if (q) {
        const matchCode = normalizeText(d.device_code).includes(q)
        const matchName = normalizeText(d.name).includes(q)
        const matchLocation = normalizeText(d.location).includes(q)
        if (!matchCode && !matchName && !matchLocation) return false
      }
      return true
    })
  }, [devices, statusFilter, deviceCodeFilter])

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
      title: <span style={{ display: 'block', textAlign: 'center' }}>Thiết bị</span>,
      key: 'device',
      width: 190,
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
          <span title={record.name} style={{ fontWeight: 600, color: '#0f172a', overflow: 'hidden', textOverflow: 'ellipsis' }}>{record.name}</span>
        </div>
      ),
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Mã thiết bị</span>,
      dataIndex: 'device_code',
      key: 'device_code',
      width: 125,
      align: 'center',
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
      title: <span style={{ display: 'block', textAlign: 'center' }}>Vị trí lắp đặt</span>,
      dataIndex: 'location',
      key: 'location',
      width: 145,
      render: (loc) => <span title={loc || ''} style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{loc || '—'}</span>,
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Trạng thái</span>,
      dataIndex: 'status',
      key: 'status',
      width: 120,
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
      title: <span style={{ display: 'block', textAlign: 'center' }}>Cấu hình nhận diện</span>,
      key: 'settings',
      width: 170,
      render: (_, record) => (
        <div style={{ lineHeight: 1.4 }}>
          <div>Ngưỡng: <strong>{record.settings?.threshold ?? '—'}%</strong></div>
          <div style={{ color: '#64748b', fontSize: 12 }}>Khóa: {record.settings?.doorDuration ?? '—'}s · Liveness: {record.settings?.liveness ? 'Bật' : 'Tắt'}</div>
        </div>
      ),
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Lần hoạt động cuối</span>,
      dataIndex: 'last_seen_at',
      key: 'last_seen_at',
      width: 115,
      align: 'center',
      render: renderCompactDateTime,
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Thao tác</span>,
      key: 'actions',
      align: 'center',
      width: canUpdateDevice || canDeleteDevice ? 145 : 85,
      render: (_, record) => (
        <Space size="small" style={{ whiteSpace: 'nowrap' }}>
          <Tooltip title="Xem chi tiết">
            <Button
              type="text"
              icon={<EyeOutlined style={{ color: '#0284c7' }} />}
              onClick={() => {
                setSelectedDeviceForDetail(record)
                setDetailModalOpen(true)
              }}
            />
          </Tooltip>
          {canUpdateDevice && (
            <Tooltip title="Sửa thiết bị">
              <Button
                type="text"
                icon={<EditOutlined style={{ color: '#0ea5e9' }} />}
                onClick={() => {
                  setSelectedDeviceForEdit(record)
                  setFormModalOpen(true)
                }}
              />
            </Tooltip>
          )}
          {canDeleteDevice && (
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
          )}
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
          {canCreateDevice && (
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
          )}
        </Space>
      </div>

      <Card style={{ marginBottom: 16 }} size="small">
        <Space wrap size="middle">
          <Input
            placeholder="Tìm theo tên, mã thiết bị, vị trí..."
            prefix={<SearchOutlined style={{ color: '#0284c7' }} />}
            value={deviceCodeFilter}
            onChange={(e) => {
              setDeviceCodeFilter(e.target.value)
              setPage(1)
            }}
            style={{ width: 260 }}
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
              type="dashed"
              danger
              icon={<ClearOutlined />}
              onClick={() => {
                setStatusFilter('')
                setDeviceCodeFilter('')
                setPage(1)
              }}
            >
              Xóa lọc
            </Button>
          )}
          <Tag color="cyan" style={{ fontWeight: 500 }}>
            Hiển thị {filteredDevices.length} / {devices.length} thiết bị
          </Tag>
        </Space>
      </Card>

      <Card styles={{ body: { padding: 0 } }} style={{ border: '1px solid #e0f2fe' }}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={filteredDevices}
          loading={loading}
          tableLayout="fixed"
          className="centered-table-header"
          pagination={{
            current: page,
            pageSize,
            total: filteredDevices.length,
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

