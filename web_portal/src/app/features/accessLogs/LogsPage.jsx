import { useEffect, useMemo, useState } from 'react'
import { EyeOutlined, ReloadOutlined } from '@ant-design/icons'
import { App as AntdApp, Button, Card, Descriptions, Modal, Select, Space, Table, Tag, Typography } from 'antd'
import deviceService from '../../services/deviceService.js'
import logService from '../../services/logService.js'
import userService from '../../services/userService.js'
import { getErrorMessage } from '../../services/apiClient.js'

const { Title, Text } = Typography
const PAGE_LIMIT = 100

function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const datePart = new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', year: '2-digit' }).format(date)
  const timePart = new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(date)
  return <span style={{ display: 'inline-flex', flexDirection: 'column', lineHeight: 1.4, whiteSpace: 'nowrap' }}><span>{datePart}</span><Text type="secondary" style={{ fontSize: 12 }}>{timePart}</Text></span>
}

export default function LogsPage() {
  const { message } = AntdApp.useApp()
  const [logs, setLogs] = useState([])
  const [users, setUsers] = useState([])
  const [devices, setDevices] = useState([])
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [resultFilter, setResultFilter] = useState('')
  const [selectedLog, setSelectedLog] = useState(null)

  const loadLogs = async ({ append = false } = {}) => {
    setLoading(true)
    try {
      const offset = append ? logs.length : 0
      const data = await logService.listLogs({ limit: PAGE_LIMIT, offset, ...(resultFilter ? { result: resultFilter } : {}) })
      setLogs((current) => append ? [...current, ...(data.items || [])] : (data.items || []))
      setHasMore(Boolean(data.has_more))
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    Promise.all([userService.listUsers(), deviceService.listAllDevices()])
      .then(([userData, deviceData]) => { setUsers(userData || []); setDevices(deviceData || []) })
      .catch((error) => message.error(getErrorMessage(error)))
  }, [])

  useEffect(() => { loadLogs() }, [resultFilter])

  const userMap = useMemo(() => Object.fromEntries(users.map((user) => [user.id, user])), [users])
  const deviceMap = useMemo(() => Object.fromEntries(devices.map((device) => [device.id, device])), [devices])

  const columns = [
    { title: 'Thời gian', dataIndex: 'access_time', key: 'access_time', width: 125, render: formatDateTime },
    { title: 'Nhân viên', key: 'user', width: 180, render: (_, record) => record.user_id ? (userMap[record.user_id]?.full_name || <Text type="secondary">Nhân viên không còn trong hệ thống</Text>) : <Tag>Khách</Tag> },
    { title: 'Thiết bị', key: 'device', width: 180, render: (_, record) => deviceMap[record.device_id]?.name || <Text code>{record.device_id?.slice(0, 8)}…</Text> },
    { title: 'Kết quả', dataIndex: 'result', key: 'result', width: 110, render: (value) => value === 'granted' ? <Tag color="success">Cho phép</Tag> : <Tag color="error">Từ chối</Tag> },
    { title: 'Tin cậy', dataIndex: 'confidence', key: 'confidence', width: 90, render: (value) => value == null ? '—' : `${Number(value).toFixed(1)}%` },
    { title: 'Thao tác', key: 'actions', width: 75, align: 'center', render: (_, record) => <Button aria-label="Xem chi tiết nhật ký" title="Xem chi tiết" type="text" icon={<EyeOutlined style={{ color: '#0284c7' }} />} onClick={() => setSelectedLog(record)} /> },
  ]

  return <div>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
      <div><Title level={3} style={{ margin: 0, color: '#0f172a' }}>Lịch sử truy cập</Title><Text type="secondary">Theo dõi các lượt nhận diện và kết quả ra vào.</Text></div>
      <Space><Select aria-label="Lọc kết quả" value={resultFilter} onChange={setResultFilter} style={{ width: 145 }} options={[{ value: '', label: 'Tất cả kết quả' }, { value: 'granted', label: 'Cho phép' }, { value: 'denied', label: 'Từ chối' }]} /><Button icon={<ReloadOutlined />} onClick={() => loadLogs()} loading={loading}>Tải lại</Button></Space>
    </div>
    <Card styles={{ body: { padding: 0 } }} style={{ borderColor: '#e0f2fe' }}>
      <Table rowKey="id" columns={columns} dataSource={logs} loading={loading} tableLayout="fixed" pagination={{ pageSize: 10, showTotal: (total) => `Đang hiển thị ${total} sự kiện` }} />
      {hasMore && <div style={{ padding: '0 16px 16px', textAlign: 'center' }}><Button onClick={() => loadLogs({ append: true })} loading={loading}>Tải thêm nhật ký</Button></div>}
    </Card>
    <Modal title="Chi tiết lượt truy cập" open={Boolean(selectedLog)} onCancel={() => setSelectedLog(null)} footer={<Button onClick={() => setSelectedLog(null)}>Đóng</Button>}>
      {selectedLog && <Descriptions bordered column={1} size="small">
        <Descriptions.Item label="Thời gian">{formatDateTime(selectedLog.access_time)}</Descriptions.Item>
        <Descriptions.Item label="Nhân viên">{selectedLog.user_id ? (userMap[selectedLog.user_id]?.full_name || selectedLog.user_id) : 'Khách'}</Descriptions.Item>
        <Descriptions.Item label="Thiết bị">{deviceMap[selectedLog.device_id]?.name || selectedLog.device_id}</Descriptions.Item>
        <Descriptions.Item label="Kết quả">{selectedLog.result === 'granted' ? 'Cho phép' : 'Từ chối'}</Descriptions.Item>
        <Descriptions.Item label="Độ tin cậy">{selectedLog.confidence == null ? '—' : `${Number(selectedLog.confidence).toFixed(1)}%`}</Descriptions.Item>
        <Descriptions.Item label="Mã sự kiện">{selectedLog.id}</Descriptions.Item>
      </Descriptions>}
    </Modal>
  </div>
}
