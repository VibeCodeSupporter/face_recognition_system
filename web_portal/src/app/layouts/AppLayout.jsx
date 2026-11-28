import { useState } from 'react'
import {
  CodeOutlined,
  DashboardOutlined,
  DeploymentUnitOutlined,
  HistoryOutlined,
  IdcardOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RestOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons'
import {
  Avatar,
  Badge,
  Breadcrumb,
  Button,
  Layout,
  Menu,
  Popconfirm,
  Space,
  Tag,
  Tooltip,
} from 'antd'
import AdminProfileModal from '../components/AdminProfileModal.jsx'
import BrandMark from '../components/BrandMark.jsx'
import { ROUTES } from '../constants/routes.js'
import useHashRoute from '../hooks/useHashRoute.js'
import { useAuth } from '../providers/AuthProvider.jsx'
import './AppLayout.css'

const { Header, Sider, Content } = Layout

const ROUTE_LABELS = {
  [ROUTES.DASHBOARD]: 'Tổng quan',
  [ROUTES.USERS]: 'Người dùng',
  [ROUTES.DEVICES]: 'Thiết bị',
  [ROUTES.SESSIONS]: 'Phiên đăng ký',
  [ROUTES.LOGS]: 'Lịch sử truy cập',
  [ROUTES.DELETION_HISTORY]: 'Lịch sử đã xóa',
}

export default function AppLayout({ children }) {
  const { path, navigate } = useHashRoute()
  const { admin, isSuperAdmin, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const [profileModalOpen, setProfileModalOpen] = useState(false)

  const currentRoute = path || ROUTES.DASHBOARD

  const menuItems = [
    {
      key: ROUTES.DASHBOARD,
      icon: <DashboardOutlined />,
      label: 'Tổng quan',
    },
    {
      key: ROUTES.USERS,
      icon: <TeamOutlined />,
      label: 'Người dùng',
    },
    {
      key: ROUTES.DEVICES,
      icon: <DeploymentUnitOutlined />,
      label: 'Thiết bị',
    },
    {
      key: ROUTES.SESSIONS,
      icon: <IdcardOutlined />,
      label: 'Phiên đăng ký',
    },
    {
      key: ROUTES.LOGS,
      icon: <HistoryOutlined />,
      label: 'Lịch sử truy cập',
    },
    {
      key: ROUTES.DELETION_HISTORY,
      icon: <RestOutlined />,
      label: 'Lịch sử đã xóa',
    },
  ]

  const handleMenuSelect = ({ key }) => {
    navigate(key)
  }

  const handleSignOut = async () => {
    await logout()
    navigate(ROUTES.LOGIN)
  }

  return (
    <Layout className="app-portal-layout">
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        width={240}
        collapsedWidth={80}
        theme="light"
        className="app-portal-sider"
      >
        <div className="sider-brand-box">
          <BrandMark size={collapsed ? 'sm' : 'md'} collapsed={collapsed} />
        </div>

        <Menu
          mode="inline"
          selectedKeys={[currentRoute]}
          items={menuItems}
          onClick={handleMenuSelect}
          style={{ borderRight: 0, marginTop: 8 }}
        />

        <div className="sider-footer-box">
          {!collapsed ? (
            <div className="sider-swagger-link">
              <a
                href="/docs"
                target="_blank"
                rel="noopener noreferrer"
                title="Mở tài liệu Swagger API"
              >
                <CodeOutlined />
                <span>Swagger API Docs</span>
              </a>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                Giờ Việt Nam · UTC+7
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center' }}>
              <Tooltip title="Mở Swagger API Docs" placement="right">
                <a
                  href="/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: '#0284c7', fontSize: 16 }}
                >
                  <CodeOutlined />
                </a>
              </Tooltip>
            </div>
          )}
        </div>
      </Sider>

      <Layout className="app-portal-main">
        <Header className="app-portal-header">
          <div className="header-left">
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              className="collapse-trigger-btn"
              title={collapsed ? 'Mở rộng thanh bên' : 'Thu nhỏ thanh bên'}
            />
            <Breadcrumb
              items={[
                { title: 'FaceAccess' },
                { title: ROUTE_LABELS[currentRoute] || 'Hệ thống' },
              ]}
            />
          </div>

          <div className="header-right">
            <Space orientation="horizontal" size="middle" align="center">
              <Badge status="success" text="Đã kết nối Backend" />

              {/* Nút xem/sửa hồ sơ Quản trị viên */}
              <Tooltip title="Bấm vào để xem và cập nhật thông tin Quản trị viên">
                <div
                  onClick={() => setProfileModalOpen(true)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    cursor: 'pointer',
                    padding: '4px 10px',
                    borderRadius: 20,
                    background: 'rgba(2, 132, 199, 0.08)',
                    border: '1px solid #bae6fd',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(2, 132, 199, 0.16)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(2, 132, 199, 0.08)'
                  }}
                >
                  <Avatar
                    size={28}
                    style={{ backgroundColor: '#0284c7', fontWeight: 600 }}
                  >
                    {(admin?.full_name || admin?.username || 'A').charAt(0).toUpperCase()}
                  </Avatar>
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#0369a1' }}>
                    {admin?.full_name || admin?.username || 'Quản trị viên'}
                  </span>
                  <Tag
                    color={isSuperAdmin ? 'gold' : 'blue'}
                    style={{ margin: 0, borderRadius: 12, fontSize: 11, fontWeight: 600 }}
                  >
                    {isSuperAdmin ? 'Cấp cao · Toàn quyền' : 'Vận hành · Xem & Embedding'}
                  </Tag>
                </div>
              </Tooltip>

              <Popconfirm
                title="Đăng xuất"
                description="Bạn có chắc chắn muốn đăng xuất khỏi hệ thống?"
                onConfirm={handleSignOut}
                okText="Đăng xuất"
                cancelText="Hủy"
                okButtonProps={{ danger: true }}
              >
                <Button
                  type="text"
                  danger
                  icon={<LogoutOutlined />}
                  title="Đăng xuất"
                >
                  <span className="signout-text">Đăng xuất</span>
                </Button>
              </Popconfirm>
            </Space>
          </div>
        </Header>

        <Content className="app-portal-content">
          <div className="content-inner">{children}</div>
        </Content>
      </Layout>

      {/* Modal Cập nhật Hồ sơ Quản trị viên */}
      <AdminProfileModal
        open={profileModalOpen}
        onClose={() => setProfileModalOpen(false)}
      />
    </Layout>
  )
}
