import { useEffect, useMemo, useState } from 'react'
import {
  ClearOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  FilterOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  SmileOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import {
  App as AntdApp,
  Avatar,
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
import userService from '../../services/userService.js'
import { getErrorMessage } from '../../services/apiClient.js'
import FaceEmbeddingModal from './FaceEmbeddingModal.jsx'
import UserDetailModal from './UserDetailModal.jsx'
import UserFormModal from './UserFormModal.jsx'

const { Title, Text } = Typography

export default function UsersPage() {
  const { message } = AntdApp.useApp()

  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)

  // Filters & Search
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('')
  const [roleFilter, setRoleFilter] = useState('')

  // Modals state
  const [formModalOpen, setFormModalOpen] = useState(false)
  const [selectedUserForEdit, setSelectedUserForEdit] = useState(null)

  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [selectedUserForDetail, setSelectedUserForDetail] = useState(null)

  const [embeddingModalOpen, setEmbeddingModalOpen] = useState(false)
  const [selectedUserForEmbedding, setSelectedUserForEmbedding] = useState(null)

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const data = await userService.listUsers()
      setUsers(data || [])
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const handleDeleteUser = async (id) => {
    try {
      await userService.deleteUser(id)
      message.success('Đã xóa người dùng thành công!')
      fetchUsers()
    } catch (error) {
      message.error(getErrorMessage(error))
    }
  }

  // Danh sách các phòng ban duy nhất từ dữ liệu thực tế
  const departmentOptions = useMemo(() => {
    const list = Array.from(
      new Set(users.map((u) => u.department?.trim()).filter(Boolean))
    ).sort((a, b) => a.localeCompare(b, 'vi'))

    return [
      { value: '', label: 'Tất cả phòng ban' },
      ...list.map((dep) => ({ value: dep, label: dep })),
    ]
  }, [users])

  // Danh sách các chức danh duy nhất từ dữ liệu thực tế
  const roleOptions = useMemo(() => {
    const list = Array.from(
      new Set(users.map((u) => u.role?.trim()).filter(Boolean))
    ).sort((a, b) => a.localeCompare(b, 'vi'))

    return [
      { value: '', label: 'Tất cả chức danh' },
      ...list.map((r) => ({ value: r, label: r })),
    ]
  }, [users])

  // Lọc đa chiều: text search, trạng thái, phòng ban, chức danh
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      // 1. Text search (tên, mã nhân viên, email)
      if (searchText.trim()) {
        const query = searchText.trim().toLowerCase()
        const matchName = (u.full_name || '').toLowerCase().includes(query)
        const matchCode = (u.user_code || '').toLowerCase().includes(query)
        const matchEmail = (u.email || '').toLowerCase().includes(query)
        if (!matchName && !matchCode && !matchEmail) return false
      }

      // 2. Lọc trạng thái
      if (statusFilter && u.status !== statusFilter) {
        return false
      }

      // 3. Lọc phòng ban
      if (departmentFilter && u.department !== departmentFilter) {
        return false
      }

      // 4. Lọc chức danh
      if (roleFilter && u.role !== roleFilter) {
        return false
      }

      return true
    })
  }, [users, searchText, statusFilter, departmentFilter, roleFilter])

  const hasActiveFilters = Boolean(
    searchText || statusFilter || departmentFilter || roleFilter
  )

  const handleResetFilters = () => {
    setSearchText('')
    setStatusFilter('')
    setDepartmentFilter('')
    setRoleFilter('')
  }

  const columns = [
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Họ và tên</span>,
      key: 'user',
      width: 150,
      render: (_, record) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap' }}>
          <Avatar
            style={{
              backgroundColor: record.status === 'active' ? '#0284c7' : '#94a3b8',
              boxShadow: '0 2px 6px rgba(2, 132, 199, 0.25)',
              fontWeight: 600,
              flexShrink: 0,
            }}
          >
            {(record.full_name || '?').charAt(0).toUpperCase()}
          </Avatar>
          <span
            style={{
              fontWeight: 600,
              color: '#0f172a',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={record.full_name}
          >
            {record.full_name}
          </span>
        </div>
      ),
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Mã nhân viên</span>,
      dataIndex: 'user_code',
      key: 'user_code',
      width: 100,
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
      title: <span style={{ display: 'block', textAlign: 'center' }}>Phòng ban</span>,
      dataIndex: 'department',
      key: 'department',
      width: 135,
      responsive: ['lg'],
      render: (dep) =>
        dep ? (
          <Tag
            style={{
              backgroundColor: '#f0f9ff',
              color: '#0284c7',
              border: '1px solid #bae6fd',
              display: 'inline-block',
              maxWidth: '100%',
              whiteSpace: dep.trim().split(/\s+/).length > 3 ? 'normal' : 'nowrap',
              overflowWrap: 'anywhere',
              lineHeight: '18px',
              verticalAlign: 'middle',
            }}
          >
            {dep}
          </Tag>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Chức danh</span>,
      dataIndex: 'role',
      key: 'role',
      width: 135,
      responsive: ['lg'],
      render: (role) =>
        role ? (
          <Tag
            style={{
              backgroundColor: '#fefce8',
              color: '#b45309',
              border: '1px solid #fde047',
              fontWeight: 500,
              display: 'inline-block',
              maxWidth: '100%',
              whiteSpace: role.trim().split(/\s+/).length > 4 ? 'normal' : 'nowrap',
              overflowWrap: 'anywhere',
              lineHeight: '18px',
              verticalAlign: 'middle',
            }}
          >
            {role}
          </Tag>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    // {
    //   title: 'Thông tin liên hệ',
    //   key: 'contact',
    //   width: 205,
    //   render: (_, record) => (
    //     <div style={{ minWidth: 0, lineHeight: 1.45 }}>
    //       <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={record.email}>{record.email || '—'}</div>
    //       {record.phone && <div style={{ color: '#64748b', fontSize: 12 }}>{record.phone}</div>}
    //     </div>
    //   ),
    // },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Trạng thái</span>,
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status) => (
        <Tag
          color={status === 'active' ? 'success' : 'default'}
          style={{ fontWeight: 500, whiteSpace: 'nowrap' }}
        >
          {status === 'active' ? 'Hoạt động' : 'Ngừng hoạt động'}
        </Tag>
      ),
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Ngày tạo</span>,
      dataIndex: 'created_at',
      key: 'created_at',
      width: 115,
      align: 'center',
      render: (date) => {
        if (!date) return <Text type="secondary">—</Text>
        const parsed = new Date(date)
        if (Number.isNaN(parsed.getTime())) return <Text type="secondary">—</Text>
        return <span style={{ display: 'inline-flex', flexDirection: 'column', lineHeight: 1.4, whiteSpace: 'nowrap' }}>
          <span>{new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', year: '2-digit' }).format(parsed)}</span>
          <span style={{ color: '#64748b', fontSize: 12 }}>{new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit' }).format(parsed)}</span>
        </span>
      },
    },
    {
      title: <span style={{ display: 'block', textAlign: 'center' }}>Thao tác</span>,
      key: 'actions',
      align: 'center',
      width: 165,
      render: (_, record) => (
        <Space size="small" style={{ whiteSpace: 'nowrap' }}>
          <Tooltip title="Xem chi tiết">
            <Button
              type="text"
              icon={<EyeOutlined style={{ color: '#0284c7' }} />}
              onClick={() => {
                setSelectedUserForDetail(record)
                setDetailModalOpen(true)
              }}
            />
          </Tooltip>
          <Tooltip title="Sửa thông tin">
            <Button
              type="text"
              icon={<EditOutlined style={{ color: '#0ea5e9' }} />}
              onClick={() => {
                setSelectedUserForEdit(record)
                setFormModalOpen(true)
              }}
            />
          </Tooltip>
          <Tooltip title="Vector khuôn mặt">
            <Button
              type="text"
              icon={<SmileOutlined style={{ color: '#eab308' }} />}
              onClick={() => {
                setSelectedUserForEmbedding(record)
                setEmbeddingModalOpen(true)
              }}
            />
          </Tooltip>
          <Popconfirm
            title="Xác nhận xóa người dùng?"
            description={`Bạn có chắc muốn xóa "${record.full_name}"? Mọi phiên đăng ký và vector khuôn mặt liên quan sẽ bị xóa.`}
            onConfirm={() => handleDeleteUser(record.id)}
            okText="Xóa"
            cancelText="Hủy"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="Xóa người dùng">
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
          marginBottom: 18,
        }}
      >
        <div>
          <Title level={3} style={{ margin: 0, color: '#0f172a' }}>
            Quản lý Người dùng
          </Title>
          <Text type="secondary">
            Danh sách nhân sự, khách và dữ liệu vector nhận diện khuôn mặt trong hệ thống.
          </Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchUsers} loading={loading}>
            Tải lại
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            style={{
              backgroundColor: '#0284c7',
              boxShadow: '0 2px 8px rgba(2, 132, 199, 0.35)',
            }}
            onClick={() => {
              setSelectedUserForEdit(null)
              setFormModalOpen(true)
            }}
          >
            Thêm người dùng
          </Button>
        </Space>
      </div>

      {/* Thanh bộ lọc đa năng */}
      <Card
        style={{
          marginBottom: 18,
          background: 'linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%)',
          borderColor: '#bae6fd',
        }}
        size="small"
      >
        <Space wrap size="middle">
          {/* 1. Tìm kiếm text */}
          <Input
            placeholder="Tìm theo tên, mã NV, email..."
            prefix={<SearchOutlined style={{ color: '#0284c7' }} />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 250 }}
            allowClear
          />

          {/* 2. Lọc Trạng thái */}
          <Select
            placeholder="Lọc trạng thái"
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ width: 170 }}
            options={[
              { value: '', label: 'Tất cả trạng thái' },
              { value: 'active', label: 'Đang hoạt động' },
              { value: 'inactive', label: 'Ngừng hoạt động' },
            ]}
          />

          {/* 3. Lọc Phòng ban */}
          <Select
            placeholder="Lọc phòng ban"
            value={departmentFilter}
            onChange={setDepartmentFilter}
            style={{ width: 200 }}
            showSearch
            optionFilterProp="label"
            options={departmentOptions}
          />

          {/* 4. Lọc Chức danh */}
          <Select
            placeholder="Lọc chức danh"
            value={roleFilter}
            onChange={setRoleFilter}
            style={{ width: 200 }}
            showSearch
            optionFilterProp="label"
            options={roleOptions}
          />

          {/* 5. Nút Xóa lọc */}
          {hasActiveFilters && (
            <Button
              type="dashed"
              danger
              icon={<ClearOutlined />}
              onClick={handleResetFilters}
            >
              Xóa lọc
            </Button>
          )}

          {/* Hiển thị số kết quả sau lọc */}
          <Tag color="cyan" style={{ marginLeft: 'auto', fontWeight: 500 }}>
            Hiển thị {filteredUsers.length} / {users.length} người dùng
          </Tag>
        </Space>
      </Card>

      <Card
        styles={{ body: { padding: 0 } }}
        style={{
          boxShadow: '0 4px 20px -2px rgba(14, 165, 233, 0.08)',
          border: '1px solid #e0f2fe',
        }}
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={filteredUsers}
          loading={loading}
          tableLayout="fixed"
          className="centered-table-header"
          pagination={{
            defaultPageSize: 20,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100'],
            showTotal: (total) => `Tổng số ${total} người dùng`,
          }}
        />
      </Card>

      <UserFormModal
        open={formModalOpen}
        user={selectedUserForEdit}
        onClose={() => setFormModalOpen(false)}
        onSuccess={fetchUsers}
      />

      <UserDetailModal
        open={detailModalOpen}
        user={selectedUserForDetail}
        onClose={() => setDetailModalOpen(false)}
      />

      <FaceEmbeddingModal
        open={embeddingModalOpen}
        user={selectedUserForEmbedding}
        onClose={() => setEmbeddingModalOpen(false)}
        onSuccess={fetchUsers}
      />
    </div>
  )
}
