import { useEffect, useState } from 'react'
import {
  CheckOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  EyeOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  SmileOutlined,
  StopOutlined,
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
import sessionService from '../../services/sessionService.js'
import userService from '../../services/userService.js'
import { getErrorMessage } from '../../services/apiClient.js'
import FaceEmbeddingModal from '../users/FaceEmbeddingModal.jsx'
import SessionCreateModal from './SessionCreateModal.jsx'
import SessionDetailModal from './SessionDetailModal.jsx'

const { Title, Text } = Typography

const STATUS_TAGS = {
  pending: { label: 'Chờ đăng ký', color: 'warning' },
  completed: { label: 'Hoàn tất', color: 'success' },
  cancelled: { label: 'Đã hủy', color: 'default' },
  expired: { label: 'Hết hạn', color: 'error' },
  failed: { label: 'Thất bại', color: 'magenta' },
}

const normalizeText = (str) =>
  (str || '')
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()

function renderCompactDateTime(value) {
  if (!value) return <Text type="secondary">—</Text>
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return <Text type="secondary">—</Text>
  const dateText = new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', year: '2-digit' }).format(date)
  const timeText = new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit' }).format(date)
  return <span style={{ display: 'inline-flex', flexDirection: 'column', lineHeight: 1.35, whiteSpace: 'nowrap' }}><span>{dateText}</span><Text type="secondary" style={{ fontSize: 12 }}>{timeText}</Text></span>
}

export default function SessionsPage() {
  const { message } = AntdApp.useApp()

  const [sessions, setSessions] = useState([])
  const [users, setUsers] = useState([])
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)

  // Filters & Pagination
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState('')
  const [userFilter, setUserFilter] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [deviceFilter, setDeviceFilter] = useState('')

  // Modals
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [selectedSessionForDetail, setSelectedSessionForDetail] = useState(null)

  const [embeddingModalOpen, setEmbeddingModalOpen] = useState(false)
  const [selectedUserForEmbedding, setSelectedUserForEmbedding] = useState(null)

  const handleSearchUser = (value) => {
    const val = (value || '').trim()
    setSearchKeyword(val)
    if (!val) {
      setUserFilter('')
      setPage(1)
      return
    }
    const q = normalizeText(val)
    const matched = users.find(
      (u) =>
        normalizeText(u.user_code) === q ||
        normalizeText(u.full_name) === q ||
        normalizeText(u.user_code).includes(q) ||
        normalizeText(u.full_name).includes(q)
    )
    if (matched) {
      setUserFilter(matched.id)
      message.info(`Đang lọc các phiên của: ${matched.full_name} · [${matched.user_code}]`)
    } else {
      message.warning(`Không tìm thấy nhân viên nào khớp với từ khóa "${val}"`)
    }
    setPage(1)
  }

  const loadLookups = async () => {
    try {
      const [userList, deviceList] = await Promise.all([
        userService.listUsers(),
        deviceService.listAllDevices(),
      ])
      setUsers(userList)
      setDevices(deviceList)
    } catch (_) {}
  }

  const fetchSessions = async () => {
    setLoading(true)
    try {
      const params = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
      }
      if (statusFilter) params.status = statusFilter
      if (userFilter) params.user_id = userFilter
      if (deviceFilter) params.device_id = deviceFilter

      const data = await sessionService.listSessions(params)
      setSessions(data.items || [])
      setTotal(data.total || (data.items || []).length)
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLookups()
  }, [])

  useEffect(() => {
    fetchSessions()
  }, [page, pageSize, statusFilter, userFilter, deviceFilter])

  const handleUpdateStatus = async (id, status) => {
    try {
      await sessionService.updateStatus(id, status)
      message.success(
        status === 'completed'
          ? 'Đã hoàn tất phiên đăng ký!'
          : status === 'cancelled'
          ? 'Đã hủy phiên đăng ký.'
          : 'Đã đánh dấu phiên thất bại.'
      )
      fetchSessions()
    } catch (error) {
      message.error(getErrorMessage(error))
    }
  }

  const handleDeleteSession = async (id) => {
    try {
      await sessionService.deleteSession(id)
      message.success('Đã xóa phiên đăng ký.')
      fetchSessions()
    } catch (error) {
      message.error(getErrorMessage(error))
    }
  }

  const handleOpenEmbedding = (userId) => {
    const user = users.find((u) => u.id === userId)
    if (user) {
      setSelectedUserForEmbedding(user)
      setEmbeddingModalOpen(true)
    } else {
      setSelectedUserForEmbedding({ id: userId, full_name: 'Người dùng', user_code: '' })
      setEmbeddingModalOpen(true)
    }
  }

  const columns = [
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Người dùng</span>,
      key: 'user',
      width: 205,
      render: (_, record) => {
        const u = users.find((item) => item.id === record.user_id)
        return u ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap' }}>
            <Tag
              style={{
                backgroundColor: '#e0f2fe',
                color: '#0369a1',
                border: '1px solid #bae6fd',
                fontWeight: 600,
                margin: 0,
                whiteSpace: 'nowrap',
              }}
            >
              {u.user_code}
            </Tag>
            <span style={{ fontWeight: 600, color: '#0f172a', whiteSpace: 'nowrap' }}>
              {u.full_name}
            </span>
          </div>
        ) : (
          <code style={{ fontSize: 12 }}>{record.user_id.slice(0, 8)}…</code>
        )
      },
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Thiết bị đăng ký</span>,
      key: 'device',
      width: 165,
      render: (_, record) => {
        const d = devices.find((item) => item.id === record.device_id)
        return d ? (
          <span title={d.name} style={{ display: 'block', fontWeight: 500, color: '#334155', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</span>
        ) : (
          <code style={{ fontSize: 12 }}>{record.device_id.slice(0, 8)}…</code>
        )
      },
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Trạng thái</span>,
      dataIndex: 'status',
      key: 'status',
      width: 125,
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
      title: <span style={{ display: 'block', textAlign: 'center' }}>Ngày tạo</span>,
      dataIndex: 'created_at',
      key: 'created_at',
      width: 115,
      align: 'center',
      render: renderCompactDateTime,
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Hết hạn</span>,
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 115,
      align: 'center',
      render: renderCompactDateTime,
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Hoàn tất lúc</span>,
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 115,
      align: 'center',
      render: renderCompactDateTime,
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Thao tác</span>,
      key: 'actions',
      align: 'center',
      width: 245,
      render: (_, record) => {
        const isPending = record.status === 'pending'
        const isNotExpired =
          !record.expires_at || new Date(record.expires_at).getTime() > Date.now()

        return (
          <Space size="small" style={{ whiteSpace: 'nowrap' }}>
            <Tooltip title="Xem chi tiết">
              <Button
                type="text"
                icon={<EyeOutlined />}
                onClick={() => {
                  setSelectedSessionForDetail(record)
                  setDetailModalOpen(true)
                }}
              />
            </Tooltip>

            {isPending && isNotExpired && (
              <>
                <Tooltip title="Nạp Vector khuôn mặt cho người này">
                  <Button
                    type="text"
                    icon={<SmileOutlined style={{ color: '#1677ff' }} />}
                    onClick={() => handleOpenEmbedding(record.user_id)}
                  />
                </Tooltip>

                <Popconfirm
                  title="Hoàn tất phiên đăng ký?"
                  description="Xác nhận đã thu nhận và lưu trữ vector khuôn mặt thành công."
                  onConfirm={() => handleUpdateStatus(record.id, 'completed')}
                  okText="Hoàn tất"
                  cancelText="Hủy"
                >
                  <Tooltip title="Hoàn tất phiên">
                    <Button
                      type="text"
                      icon={<CheckOutlined style={{ color: '#52c41a' }} />}
                    />
                  </Tooltip>
                </Popconfirm>

                <Popconfirm
                  title="Hủy phiên đăng ký?"
                  onConfirm={() => handleUpdateStatus(record.id, 'cancelled')}
                  okText="Hủy phiên"
                  cancelText="Đóng"
                >
                  <Tooltip title="Hủy phiên">
                    <Button type="text" icon={<StopOutlined />} />
                  </Tooltip>
                </Popconfirm>

                <Popconfirm
                  title="Đánh dấu thất bại?"
                  description="Phiên đăng ký không thành công do lỗi camera hoặc chất lượng ảnh."
                  onConfirm={() => handleUpdateStatus(record.id, 'failed')}
                  okText="Xác nhận thất bại"
                  cancelText="Hủy"
                  okButtonProps={{ danger: true }}
                >
                  <Tooltip title="Đánh dấu thất bại">
                    <Button
                      type="text"
                      danger
                      icon={<CloseCircleOutlined />}
                    />
                  </Tooltip>
                </Popconfirm>
              </>
            )}

            <Popconfirm
              title="Xóa phiên đăng ký?"
              description="Bản ghi phiên sẽ bị xóa vĩnh viễn khỏi hệ thống."
              onConfirm={() => handleDeleteSession(record.id)}
              okText="Xóa"
              cancelText="Hủy"
              okButtonProps={{ danger: true }}
            >
              <Tooltip title="Xóa phiên">
                <Button type="text" danger icon={<DeleteOutlined />} />
              </Tooltip>
            </Popconfirm>
          </Space>
        )
      },
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
            Phiên Đăng ký Khuôn mặt
          </Title>
          <Text type="secondary">
            Khởi tạo phiên chụp ảnh khuôn mặt tại thiết bị cửa và nạp vector nhận diện vào hệ thống.
          </Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchSessions} loading={loading}>
            Tải lại
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
            Tạo phiên mới
          </Button>
        </Space>
      </div>

      <Card style={{ marginBottom: 16 }} size="small">
        <Space wrap size="middle">
          <Input.Search
            placeholder="Tìm theo Tên hoặc Mã NV..."
            allowClear
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            onSearch={handleSearchUser}
            style={{ width: 250 }}
          />

          <Select
            placeholder="Lọc theo người dùng (Tên / Mã NV)"
            value={userFilter || undefined}
            allowClear
            onChange={(val) => {
              setUserFilter(val || '')
              const found = users.find((u) => u.id === val)
              setSearchKeyword(found ? found.user_code : '')
              setPage(1)
            }}
            style={{ minWidth: 280 }}
            showSearch
            filterOption={(input, option) => {
              if (!input) return true
              const q = normalizeText(input)
              const label = normalizeText(option?.label)
              const code = normalizeText(option?.userCode)
              const name = normalizeText(option?.fullName)
              return label.includes(q) || code.includes(q) || name.includes(q)
            }}
            options={users.map((u) => ({
              value: u.id,
              label: `[${u.user_code}] ${u.full_name}${u.department ? ` · ${u.department}` : ''}`,
              fullName: u.full_name,
              userCode: u.user_code,
            }))}
          />

          <Select
            placeholder="Lọc theo thiết bị"
            value={deviceFilter || undefined}
            allowClear
            onChange={(val) => {
              setDeviceFilter(val || '')
              setPage(1)
            }}
            style={{ width: 220 }}
            showSearch
            optionFilterProp="label"
            options={devices.map((d) => ({
              value: d.id,
              label: `${d.name} · ${d.device_code}`,
            }))}
          />

          <Select
            placeholder="Trạng thái phiên"
            value={statusFilter || undefined}
            allowClear
            onChange={(val) => {
              setStatusFilter(val || '')
              setPage(1)
            }}
            style={{ width: 170 }}
            options={[
              { value: 'pending', label: 'Chờ đăng ký' },
              { value: 'completed', label: 'Hoàn tất' },
              { value: 'cancelled', label: 'Đã hủy' },
              { value: 'expired', label: 'Hết hạn' },
              { value: 'failed', label: 'Thất bại' },
            ]}
          />

          {(statusFilter || userFilter || deviceFilter || searchKeyword) && (
            <Button
              type="link"
              onClick={() => {
                setStatusFilter('')
                setUserFilter('')
                setSearchKeyword('')
                setDeviceFilter('')
                setPage(1)
              }}
            >
              Xóa tất cả lọc
            </Button>
          )}

          {userFilter && (
            <Tag
              color="processing"
              closable
              onClose={() => {
                setUserFilter('')
                setSearchKeyword('')
                setPage(1)
              }}
              style={{ fontWeight: 500 }}
            >
              Lọc nhân viên:{' '}
              {(() => {
                const u = users.find((item) => item.id === userFilter)
                return u ? `${u.full_name} (${u.user_code})` : userFilter
              })()}
            </Tag>
          )}
        </Space>
      </Card>

      <Card styles={{ body: { padding: 0 } }} style={{ border: '1px solid #e0f2fe' }}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={sessions}
          loading={loading}
          tableLayout="fixed"
          className="centered-table-header"
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
            showTotal: (tot) => `Tổng số ${tot} phiên đăng ký`,
          }}
        />
      </Card>

      <SessionCreateModal
        open={createModalOpen}
        users={users}
        devices={devices}
        onClose={() => setCreateModalOpen(false)}
        onSuccess={() => {
          fetchSessions()
          loadLookups()
        }}
      />

      <SessionDetailModal
        open={detailModalOpen}
        session={selectedSessionForDetail}
        users={users}
        devices={devices}
        onClose={() => setDetailModalOpen(false)}
      />

      <FaceEmbeddingModal
        open={embeddingModalOpen}
        user={selectedUserForEmbedding}
        onClose={() => setEmbeddingModalOpen(false)}
        onSuccess={fetchSessions}
      />
    </div>
  )
}

