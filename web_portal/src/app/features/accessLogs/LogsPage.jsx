import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ClearOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EyeOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import {
  App as AntdApp,
  Avatar,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd'
import dayjs from 'dayjs'
import deviceService from '../../services/deviceService.js'
import logService from '../../services/logService.js'
import userService from '../../services/userService.js'
import { formatDateTimeVN, getErrorMessage } from '../../services/apiClient.js'
import { useAuth } from '../../providers/AuthProvider.jsx'
import LogsDeleteModal from './LogsDeleteModal.jsx'

const { Title, Text } = Typography
const { RangePicker } = DatePicker
const PAGE_LIMIT = 100

const normalizeText = (str) =>
  (str || '')
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()

function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const datePart = new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', year: '2-digit' }).format(date)
  const timePart = new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(date)
  return <span style={{ display: 'inline-flex', flexDirection: 'column', lineHeight: 1.4, whiteSpace: 'nowrap' }}><span>{datePart}</span><Text type="secondary" style={{ fontSize: 12 }}>{timePart}</Text></span>
}

function escapeCsvCell(value) {
  const str = String(value ?? '')
  return `"${str.replace(/"/g, '""')}"`
}

export default function LogsPage() {
  const { message } = AntdApp.useApp()
  const { isSuperAdmin } = useAuth()

  const [logs, setLogs] = useState([])
  const [users, setUsers] = useState([])
  const [devices, setDevices] = useState([])
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)

  // Filters
  const [resultFilter, setResultFilter] = useState('')
  const [userFilter, setUserFilter] = useState('')
  const [deviceFilter, setDeviceFilter] = useState('')
  const [timeRange, setTimeRange] = useState(null)

  // Modals
  const [selectedLog, setSelectedLog] = useState(null)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)

  const buildFilterParams = useCallback(() => {
    const params = {}
    if (resultFilter) params.result = resultFilter
    if (userFilter) params.user_id = userFilter
    if (deviceFilter) params.device_id = deviceFilter
    if (Array.isArray(timeRange) && timeRange[0] && timeRange[1]) {
      params.start_time = `${timeRange[0].format('YYYY-MM-DD[T]HH:mm:ss')}.000+07:00`
      params.end_time = `${timeRange[1].format('YYYY-MM-DD[T]HH:mm:ss')}.999+07:00`
    }
    return params
  }, [resultFilter, userFilter, deviceFilter, timeRange])

  const loadLogs = useCallback(async ({ append = false } = {}) => {
    setLoading(true)
    try {
      const offset = append ? logs.length : 0
      const data = await logService.listLogs({
        limit: PAGE_LIMIT,
        offset,
        ...buildFilterParams(),
      })
      setLogs((current) => append ? [...current, ...(data.items || [])] : (data.items || []))
      setHasMore(Boolean(data.has_more))
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [buildFilterParams, logs.length, message])

  const filterStateRef = useRef({ resultFilter, userFilter, deviceFilter, timeRange, loadLogs })
  filterStateRef.current = { resultFilter, userFilter, deviceFilter, timeRange, loadLogs }

  useEffect(() => {
    Promise.all([userService.listUsers(), deviceService.listAllDevices()])
      .then(([userData, deviceData]) => { setUsers(userData || []); setDevices(deviceData || []) })
      .catch((error) => message.error(getErrorMessage(error)))
  }, [message])

  useEffect(() => {
    loadLogs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resultFilter, userFilter, deviceFilter, timeRange])

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = (window.location.port === '3000' || window.location.port === '5173') ? '127.0.0.1:5000' : window.location.host
    const wsUrl = `${protocol}//${wsHost}/api/v1/ws/portal`
    let ws = null
    let timer = null

    function connect() {
      try {
        ws = new WebSocket(wsUrl)
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.event === 'NEW_ACCESS_LOG' && data.log) {
              const incoming = data.log
              const { resultFilter: rf, userFilter: uf, deviceFilter: df, timeRange: tr } = filterStateRef.current
              const matchesFilters =
                (!rf || incoming.result === rf) &&
                (!uf || incoming.user_id === uf) &&
                (!df || incoming.device_id === df) &&
                (!Array.isArray(tr) || !tr[0] || !tr[1] || (
                  new Date(incoming.access_time).getTime() >= tr[0].valueOf() &&
                  new Date(incoming.access_time).getTime() <= tr[1].valueOf()
                ))
              if (matchesFilters) {
                setLogs((prev) => [incoming, ...prev.filter((l) => l.id !== incoming.id)])
              }
              const resText = incoming.result === 'granted' ? 'Cho phép' : 'Từ chối'
              message.info(`Lượt truy cập mới: ${resText}`)
            } else if (data.event === 'LOGS_DELETED') {
              filterStateRef.current.loadLogs()
            }
          } catch (_) {}
        }
        ws.onclose = () => {
          timer = setTimeout(connect, 3000)
        }
      } catch (_) {
        timer = setTimeout(connect, 3000)
      }
    }
    connect()

    return () => {
      if (timer) clearTimeout(timer)
      if (ws) {
        ws.onclose = null
        ws.close()
      }
    }
  }, [message])

  const userMap = useMemo(() => Object.fromEntries(users.map((user) => [user.id, user])), [users])
  const deviceMap = useMemo(() => Object.fromEntries(devices.map((device) => [device.id, device])), [devices])

  const handleExportCsv = async () => {
    setExporting(true)
    try {
      const items = await logService.exportAllLogs(buildFilterParams())
      if (!items.length) {
        message.info('Không có bản ghi nào phù hợp để truy xuất.')
        return
      }
      const headers = ['Thời gian (UTC+7)', 'Mã nhân viên', 'Họ và tên', 'Thiết bị', 'Kết quả', 'Độ tin cậy (%)', 'Mã sự kiện']
      const rows = items.map((item) => {
        const u = item.user_id ? userMap[item.user_id] : null
        const d = deviceMap[item.device_id]
        return [
          formatDateTimeVN(item.access_time),
          u?.user_code || (item.user_id ? 'N/A' : 'Khách'),
          u?.full_name || (item.user_id ? item.user_id : 'Khách'),
          d ? `${d.name} (${d.device_code})` : item.device_id,
          item.result === 'granted' ? 'Cho phép' : 'Từ chối',
          item.confidence == null ? '' : Number(item.confidence).toFixed(1),
          item.id,
        ].map(escapeCsvCell).join(',')
      })
      const csvContent = '\uFEFF' + [headers.map(escapeCsvCell).join(','), ...rows].join('\r\n')
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `lich_su_truy_cap_${dayjs().format('YYYYMMDD_HHmmss')}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      message.success(`Đã truy xuất ${items.length} bản ghi lịch sử truy cập!`)
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setExporting(false)
    }
  }

  const hasActiveFilters = Boolean(resultFilter || userFilter || deviceFilter || timeRange)

  const handleResetFilters = () => {
    setResultFilter('')
    setUserFilter('')
    setDeviceFilter('')
    setTimeRange(null)
  }

  const rangePresets = useMemo(() => [
    { label: '1 giờ qua', value: [dayjs().subtract(1, 'hour'), dayjs()] },
    { label: 'Hôm nay', value: [dayjs().startOf('day'), dayjs().endOf('day')] },
    { label: 'Hôm qua', value: [dayjs().subtract(1, 'day').startOf('day'), dayjs().subtract(1, 'day').endOf('day')] },
    { label: '7 ngày qua', value: [dayjs().subtract(6, 'day').startOf('day'), dayjs().endOf('day')] },
    { label: 'Tháng này', value: [dayjs().startOf('month'), dayjs().endOf('month')] },
    { label: 'Tháng trước', value: [dayjs().subtract(1, 'month').startOf('month'), dayjs().subtract(1, 'month').endOf('month')] },
  ], [])

  const columns = [
    { title: 'Thời gian', dataIndex: 'access_time', key: 'access_time', width: 125, render: formatDateTime },
    {
      title: 'Nhân viên / Ảnh',
      key: 'user',
      width: 220,
      render: (_, record) => {
        if (!record.user_id) return <Tag>Khách</Tag>
        const u = userMap[record.user_id]
        if (!u) return <Text type="secondary">Nhân viên không còn trong hệ thống</Text>
        const initial = (u.full_name || '?').charAt(0).toUpperCase()
        return (
          <Space>
            <Avatar size="small" style={{ backgroundColor: '#0284c7', color: '#fff', fontWeight: 600 }}>
              {initial}
            </Avatar>
            <span>{u.full_name}</span>
            {u.user_code && <Text type="secondary" style={{ fontSize: 11 }}>({u.user_code})</Text>}
          </Space>
        )
      },
    },
    { title: 'Thiết bị', key: 'device', width: 180, render: (_, record) => deviceMap[record.device_id]?.name || <Text code>{record.device_id?.slice(0, 8)}…</Text> },
    { title: 'Kết quả', dataIndex: 'result', key: 'result', width: 110, render: (value) => value === 'granted' ? <Tag color="success">Cho phép</Tag> : <Tag color="error">Từ chối</Tag> },
    { title: 'Tin cậy', dataIndex: 'confidence', key: 'confidence', width: 90, render: (value) => value == null ? '—' : `${Number(value).toFixed(1)}%` },
    { title: 'Thao tác', key: 'actions', width: 75, align: 'center', render: (_, record) => <Button aria-label="Xem chi tiết nhật ký" title="Xem chi tiết" type="text" icon={<EyeOutlined style={{ color: '#0284c7' }} />} onClick={() => setSelectedLog(record)} /> },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <Title level={3} style={{ margin: 0, color: '#0f172a' }}>Lịch sử truy cập</Title>
          <Text type="secondary">Tra cứu, truy xuất báo cáo theo khoảng thời gian và theo dõi lượt ra vào thời gian thực.</Text>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined />} onClick={() => loadLogs()} loading={loading}>
            Tải lại
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExportCsv}
            loading={exporting}
          >
            Truy xuất CSV
          </Button>
          {isSuperAdmin && (
            <Button
              type="primary"
              danger
              icon={<DeleteOutlined />}
              onClick={() => setDeleteModalOpen(true)}
            >
              Xóa lịch sử
            </Button>
          )}
        </Space>
      </div>

      {/* Bộ lọc tìm kiếm & Truy xuất theo khoảng thời gian */}
      <Card
        size="small"
        style={{
          marginBottom: 16,
          background: 'linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%)',
          borderColor: '#bae6fd',
        }}
      >
        <Space wrap size="middle">
          <RangePicker
            value={timeRange}
            onChange={(vals) => setTimeRange(vals)}
            showTime={{ format: 'HH:mm' }}
            format="DD/MM/YYYY HH:mm"
            presets={rangePresets}
            placeholder={['Từ thời điểm', 'Đến thời điểm']}
            allowClear
            style={{ width: 320 }}
          />

          <Select
            placeholder="Tìm nhân viên (Tên / Mã NV)..."
            value={userFilter || undefined}
            allowClear
            showSearch
            onChange={(val) => setUserFilter(val || '')}
            style={{ width: 240 }}
            filterOption={(input, option) => {
              if (!input) return true
              const q = normalizeText(input)
              return (
                normalizeText(option?.label).includes(q) ||
                normalizeText(option?.userCode).includes(q) ||
                normalizeText(option?.fullName).includes(q)
              )
            }}
            options={users.map((u) => ({
              value: u.id,
              label: `[${u.user_code}] ${u.full_name}`,
              userCode: u.user_code,
              fullName: u.full_name,
            }))}
          />

          <Select
            placeholder="Lọc theo thiết bị"
            value={deviceFilter || undefined}
            allowClear
            showSearch
            optionFilterProp="label"
            onChange={(val) => setDeviceFilter(val || '')}
            style={{ width: 200 }}
            options={devices.map((d) => ({
              value: d.id,
              label: `${d.name} · ${d.device_code}`,
            }))}
          />

          <Select
            aria-label="Lọc kết quả"
            value={resultFilter}
            onChange={setResultFilter}
            style={{ width: 150 }}
            options={[
              { value: '', label: 'Tất cả kết quả' },
              { value: 'granted', label: 'Cho phép' },
              { value: 'denied', label: 'Từ chối' },
            ]}
          />

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

          <Tag color="cyan" style={{ fontWeight: 500 }}>
            Đang hiển thị {logs.length}{hasMore ? '+' : ''} sự kiện
          </Tag>
        </Space>
      </Card>

      <Card styles={{ body: { padding: 0 } }} style={{ borderColor: '#e0f2fe' }}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={logs}
          loading={loading}
          tableLayout="fixed"
          className="centered-table-header"
          pagination={{ pageSize: 10, showSizeChanger: true, pageSizeOptions: ['10', '20', '50', '100'], showTotal: (total) => `Đang hiển thị ${total} sự kiện` }}
        />
        {hasMore && (
          <div style={{ padding: '0 16px 16px', textAlign: 'center' }}>
            <Button onClick={() => loadLogs({ append: true })} loading={loading}>
              Tải thêm nhật ký
            </Button>
          </div>
        )}
      </Card>

      <Modal title="Chi tiết lượt truy cập" open={Boolean(selectedLog)} onCancel={() => setSelectedLog(null)} footer={<Button onClick={() => setSelectedLog(null)}>Đóng</Button>}>
        {selectedLog && <Descriptions bordered column={1} size="small">
          <Descriptions.Item label="Thời gian">{formatDateTime(selectedLog.access_time)}</Descriptions.Item>
          <Descriptions.Item label="Nhân viên">
            {selectedLog.user_id ? (
              <Space>
                <Avatar size="default" style={{ backgroundColor: '#0284c7', color: '#fff', fontWeight: 600 }}>
                  {((userMap[selectedLog.user_id]?.full_name) || '?').charAt(0).toUpperCase()}
                </Avatar>
                <div>
                  <div><strong>{userMap[selectedLog.user_id]?.full_name || selectedLog.user_id}</strong></div>
                  {userMap[selectedLog.user_id]?.user_code && <Text type="secondary" style={{ fontSize: 12 }}>Mã NV: {userMap[selectedLog.user_id].user_code}</Text>}
                </div>
              </Space>
            ) : <Tag>Khách</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="Thiết bị">{deviceMap[selectedLog.device_id]?.name || selectedLog.device_id}</Descriptions.Item>
          <Descriptions.Item label="Kết quả">{selectedLog.result === 'granted' ? <Tag color="success">Cho phép</Tag> : <Tag color="error">Từ chối</Tag>}</Descriptions.Item>
          <Descriptions.Item label="Độ tin cậy">{selectedLog.confidence == null ? '—' : `${Number(selectedLog.confidence).toFixed(1)}%`}</Descriptions.Item>
          <Descriptions.Item label="Mã sự kiện">{selectedLog.id}</Descriptions.Item>
        </Descriptions>}
      </Modal>

      {isSuperAdmin && (
        <LogsDeleteModal
          open={deleteModalOpen}
          devices={devices}
          onClose={() => setDeleteModalOpen(false)}
          onDeleted={() => loadLogs()}
        />
      )}
    </div>
  )
}
