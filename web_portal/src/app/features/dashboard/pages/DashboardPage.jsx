import { useEffect, useState } from 'react'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloudServerOutlined,
  DashboardOutlined,
  DeploymentUnitOutlined,
  FieldTimeOutlined,
  HistoryOutlined,
  IdcardOutlined,
  PlusOutlined,
  ReloadOutlined,
  RightOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  Col,
  Progress,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd'
import { ROUTES } from '../../../constants/routes.js'
import useHashRoute from '../../../hooks/useHashRoute.js'
import deviceService from '../../../services/deviceService.js'
import logService from '../../../services/logService.js'
import sessionService from '../../../services/sessionService.js'
import userService from '../../../services/userService.js'
import apiClient, { formatDateTimeVN } from '../../../services/apiClient.js'
import { useAuth } from '../../../providers/AuthProvider.jsx'

const { Title, Text, Paragraph } = Typography

export default function DashboardPage() {
  const { navigate } = useHashRoute()
  const { hasPermission } = useAuth()
  const canCreateSession = hasPermission('sessions:create')

  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    totalDevices: 0,
    onlineDevices: 0,
    pendingSessions: 0,
    totalLogs: 0,
    grantedLogs: 0,
    deniedLogs: 0,
  })
  const [recentLogs, setRecentLogs] = useState([])
  const [userMap, setUserMap] = useState({})
  const [deviceMap, setDeviceMap] = useState({})
  const [backendHealth, setBackendHealth] = useState({ ok: false, checking: true })

  const loadDashboardData = async () => {
    setLoading(true)
    try {
      // 1. Kiểm tra health
      try {
        await apiClient.request('/health')
        setBackendHealth({ ok: true, checking: false })
      } catch (_) {
        setBackendHealth({ ok: false, checking: false })
      }

      // 2. Tải users, devices, sessions, logs
      const [users, devicesData, sessionsData, logsData] = await Promise.all([
        userService.listUsers().catch(() => []),
        deviceService.listDevices({ limit: 100 }).catch(() => ({ items: [] })),
        sessionService.listSessions({ limit: 100 }).catch(() => ({ items: [] })),
        logService.listLogs({ limit: 5 }).catch(() => ({ items: [], total: 0 })),
      ])

      const activeUsersCount = users.filter((u) => u.status === 'active').length
      const devices = devicesData.items || []
      const onlineDevicesCount = devices.filter((d) => d.status === 'online').length
      const sessions = sessionsData.items || []
      const pendingSessionsCount = sessions.filter((s) => s.status === 'pending').length

      // Lấy thêm tổng số logs
      const totalLogsCount = logsData.total || (logsData.items || []).length
      const logs = logsData.items || []

      // Tạo map lookup
      const uMap = {}
      users.forEach((u) => {
        uMap[u.id] = u
      })
      const dMap = {}
      devices.forEach((d) => {
        dMap[d.id] = d
      })

      setUserMap(uMap)
      setDeviceMap(dMap)
      setRecentLogs(logs)

      setStats({
        totalUsers: users.length,
        activeUsers: activeUsersCount,
        totalDevices: devices.length,
        onlineDevices: onlineDevicesCount,
        pendingSessions: pendingSessionsCount,
        totalLogs: totalLogsCount,
        grantedLogs: logs.filter((l) => l.result === 'granted').length,
        deniedLogs: logs.filter((l) => l.result === 'denied').length,
      })
    } catch (_) {
      // lỗi load dashboard
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboardData()
  }, [])

  const columns = [
    {
      title: 'Người dùng',
      key: 'user',
      render: (_, record) => {
        if (!record.user_id) return <Tag>Người lạ</Tag>
        const u = userMap[record.user_id]
        return u ? (
          <Space>
            <Avatar size="small" style={{ backgroundColor: '#1677ff' }}>
              {(u.full_name || '?').charAt(0).toUpperCase()}
            </Avatar>
            <span>{u.full_name}</span>
          </Space>
        ) : (
          <code>{record.user_id.slice(0, 8)}…</code>
        )
      },
    },
    {
      title: 'Thiết bị cửa',
      key: 'device',
      render: (_, record) => {
        const d = deviceMap[record.device_id]
        return d ? d.name : <code>{record.device_id.slice(0, 8)}…</code>
      },
    },
    {
      title: 'Kết quả',
      dataIndex: 'result',
      key: 'result',
      render: (res) =>
        res === 'granted' ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            Cho phép
          </Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="error">
            Từ chối
          </Tag>
        ),
    },
    {
      title: 'Thời gian',
      dataIndex: 'access_time',
      key: 'access_time',
      render: (date) => formatDateTimeVN(date),
    },
  ]

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
        }}
      >
        <div>
          <Title level={3} style={{ margin: 0 }}>
            Tổng quan Hệ thống FaceAccess
          </Title>
          <Text type="secondary">
            Bảng điều khiển trung tâm kiểm soát ra vào và nhận diện khuôn mặt thời gian thực.
          </Text>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadDashboardData} loading={loading}>
          Cập nhật số liệu
        </Button>
      </div>

      {/* Backend Status Bar */}
      <div style={{ marginBottom: 20 }}>
        <Alert
          type={backendHealth.ok ? 'success' : 'warning'}
          showIcon
          icon={backendHealth.ok ? <CloudServerOutlined /> : <CloudServerOutlined />}
          message={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>
                Máy chủ Backend Cloud:{' '}
                <strong>{backendHealth.ok ? 'Đang hoạt động & Kết nối CSDL' : 'Đang kiểm tra kết nối...'}</strong>
              </span>
              <Badge status={backendHealth.ok ? 'processing' : 'warning'} text="FastAPI + Supabase" />
            </div>
          }
        />
      </div>

      {/* Metric Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            onClick={() => navigate(ROUTES.USERS)}
            style={{
              cursor: 'pointer',
              borderTop: '4px solid #0284c7',
              background: 'linear-gradient(180deg, #f0f9ff 0%, #ffffff 100%)',
              boxShadow: '0 4px 14px rgba(2, 132, 199, 0.08)',
            }}
          >
            <Statistic
              title="Tổng số Người dùng"
              value={stats.totalUsers}
              prefix={<TeamOutlined style={{ color: '#0284c7' }} />}
              suffix={
                <Text type="secondary" style={{ fontSize: 13 }}>
                  ({stats.activeUsers} hoạt động)
                </Text>
              }
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            onClick={() => navigate(ROUTES.DEVICES)}
            style={{
              cursor: 'pointer',
              borderTop: '4px solid #eab308',
              background: 'linear-gradient(180deg, #fefce8 0%, #ffffff 100%)',
              boxShadow: '0 4px 14px rgba(234, 179, 8, 0.08)',
            }}
          >
            <Statistic
              title="Thiết bị Cửa (Edge Devices)"
              value={stats.totalDevices}
              prefix={<DeploymentUnitOutlined style={{ color: '#eab308' }} />}
              suffix={
                <Text type="secondary" style={{ fontSize: 13 }}>
                  ({stats.onlineDevices} Online)
                </Text>
              }
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            onClick={() => navigate(ROUTES.SESSIONS)}
            style={{
              cursor: 'pointer',
              borderTop: '4px solid #0ea5e9',
              background: 'linear-gradient(180deg, #f0f9ff 0%, #ffffff 100%)',
              boxShadow: '0 4px 14px rgba(14, 165, 233, 0.08)',
            }}
          >
            <Statistic
              title="Phiên đăng ký khuôn mặt"
              value={stats.pendingSessions}
              prefix={<IdcardOutlined style={{ color: '#0ea5e9' }} />}
              suffix={
                <Text type="secondary" style={{ fontSize: 13 }}>
                  đang chờ xử lý
                </Text>
              }
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            onClick={() => navigate(ROUTES.LOGS)}
            style={{
              cursor: 'pointer',
              borderTop: '4px solid #f59e0b',
              background: 'linear-gradient(180deg, #fffbeb 0%, #ffffff 100%)',
              boxShadow: '0 4px 14px rgba(245, 158, 11, 0.08)',
            }}
          >
            <Statistic
              title="Lượt truy cập ghi nhận"
              value={stats.totalLogs}
              prefix={<HistoryOutlined style={{ color: '#f59e0b' }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* Quick Actions & Recent Activities */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <HistoryOutlined style={{ color: '#0284c7' }} />
                <span>Lượt ra vào gần nhất</span>
              </div>
            }
            extra={
              <Button type="link" onClick={() => navigate(ROUTES.LOGS)} style={{ color: '#0284c7' }}>
                Xem tất cả <RightOutlined />
              </Button>
            }
            styles={{ body: { padding: 0 } }}
          >
            <Table
              rowKey="id"
              columns={columns}
              dataSource={recentLogs}
              pagination={false}
              loading={loading}
              locale={{ emptyText: 'Chưa có lượt truy cập nào' }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <RightOutlined style={{ color: '#0284c7' }} />
                <span>Lối tắt thao tác nhanh</span>
              </div>
            }
            style={{
              height: '100%',
              background: '#ffffff',
              border: '1px solid #e0f2fe',
              boxShadow: '0 4px 16px rgba(14, 165, 233, 0.05)',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[
                {
                  title: 'Quản lý danh sách người dùng',
                  desc: 'Tra cứu, thêm mới và quản lý nhân sự',
                  icon: <TeamOutlined style={{ fontSize: 20, color: '#0284c7' }} />,
                  route: ROUTES.USERS,
                  hoverBg: '#f0f9ff',
                  borderColor: '#7dd3fc',
                },
                {
                  title: 'Quản lý & cấu hình thiết bị',
                  desc: 'Cài đặt ngưỡng nhận diện và thời gian mở cửa',
                  icon: <DeploymentUnitOutlined style={{ fontSize: 20, color: '#eab308' }} />,
                  route: ROUTES.DEVICES,
                  hoverBg: '#fefce8',
                  borderColor: '#fde047',
                },
                {
                  title: canCreateSession ? 'Tạo phiên đăng ký khuôn mặt' : 'Tra cứu phiên đăng ký khuôn mặt',
                  desc: canCreateSession
                    ? 'Khởi tạo phiên chụp ảnh và nạp vector tại cửa'
                    : 'Xem danh sách và trạng thái phiên đăng ký khuôn mặt',
                  icon: <PlusOutlined style={{ fontSize: 20, color: '#0ea5e9' }} />,
                  route: ROUTES.SESSIONS,
                  hoverBg: '#f0fdf4',
                  borderColor: '#86efac',
                },
                {
                  title: 'Tra cứu nhật ký kiểm soát cửa',
                  desc: 'Xem lịch sử ra vào và độ tin cậy thời gian thực',
                  icon: <HistoryOutlined style={{ fontSize: 20, color: '#f59e0b' }} />,
                  route: ROUTES.LOGS,
                  hoverBg: '#fffbeb',
                  borderColor: '#fed7aa',
                },
              ].map((item, idx) => (
                <div
                  key={idx}
                  onClick={() => navigate(item.route)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 14,
                    padding: '13px 15px',
                    borderRadius: 10,
                    background: '#ffffff',
                    border: '1px solid #e2e8f0',
                    cursor: 'pointer',
                    transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = item.hoverBg
                    e.currentTarget.style.borderColor = item.borderColor
                    e.currentTarget.style.transform = 'translateY(-2px)'
                    e.currentTarget.style.boxShadow = '0 6px 16px rgba(14, 165, 233, 0.12)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = '#ffffff'
                    e.currentTarget.style.borderColor = '#e2e8f0'
                    e.currentTarget.style.transform = 'translateY(0)'
                    e.currentTarget.style.boxShadow = 'none'
                  }}
                >
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 10,
                      background: 'rgba(255, 255, 255, 0.9)',
                      border: '1px solid #e2e8f0',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {item.icon}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 14, color: '#0f172a' }}>
                      {item.title}
                    </div>
                    <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                      {item.desc}
                    </div>
                  </div>
                  <RightOutlined style={{ fontSize: 12, color: '#94a3b8' }} />
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
