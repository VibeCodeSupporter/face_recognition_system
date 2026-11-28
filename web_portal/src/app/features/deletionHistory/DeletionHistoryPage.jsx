import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ClearOutlined,
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  RestOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import {
  App as AntdApp,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd'
import dayjs from 'dayjs'
import deletionHistoryService from '../../services/deletionHistoryService.js'
import { formatDateTimeVN, getErrorMessage } from '../../services/apiClient.js'
import { useAuth } from '../../providers/AuthProvider.jsx'

const { Title, Text } = Typography
const { RangePicker } = DatePicker
const PAGE_LIMIT = 50

const ENTITY_CONFIG = {
  user: { label: 'Người dùng', color: 'blue' },
  device: { label: 'Thiết bị', color: 'cyan' },
  session: { label: 'Phiên đăng ký', color: 'purple' },
  access_log: { label: 'Lịch sử truy cập', color: 'orange' },
}

export default function DeletionHistoryPage() {
  const { message } = AntdApp.useApp()
  const { isSuperAdmin } = useAuth()

  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  const [entityType, setEntityType] = useState('')
  const [searchText, setSearchText] = useState('')
  const [timeRange, setTimeRange] = useState(null)
  const [selectedEntry, setSelectedEntry] = useState(null)

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    try {
      const params = {
        limit: Math.min(pageSize, PAGE_LIMIT),
        offset: (page - 1) * pageSize,
      }
      if (entityType) params.entity_type = entityType
      if (searchText.trim()) params.search = searchText.trim()
      if (Array.isArray(timeRange) && timeRange[0] && timeRange[1]) {
        params.start_time = `${timeRange[0].format('YYYY-MM-DD[T]HH:mm:ss')}.000+07:00`
        params.end_time = `${timeRange[1].format('YYYY-MM-DD[T]HH:mm:ss')}.999+07:00`
      }
      const data = await deletionHistoryService.listHistory(params)
      setItems(data.items || [])
      setTotal(data.total || 0)
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [entityType, message, page, pageSize, searchText, timeRange])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

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
            if (data.event === 'DELETION_HISTORY_CREATED') {
              fetchHistory()
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
  }, [fetchHistory])

  const handleClearHistory = async () => {
    try {
      const res = await deletionHistoryService.clearHistory()
      message.success(`Đã dọn sạch ${res.cleared_count || 0} bản ghi lịch sử đã xóa.`)
      setPage(1)
      fetchHistory()
    } catch (error) {
      message.error(getErrorMessage(error))
    }
  }

  const rangePresets = useMemo(() => [
    { label: 'Hôm nay', value: [dayjs().startOf('day'), dayjs().endOf('day')] },
    { label: '7 ngày qua', value: [dayjs().subtract(6, 'day').startOf('day'), dayjs().endOf('day')] },
    { label: 'Tháng này', value: [dayjs().startOf('month'), dayjs().endOf('month')] },
  ], [])

  const hasActiveFilters = Boolean(entityType || searchText.trim() || timeRange)

  const columns = [
    {
      title: 'Thời gian xóa',
      dataIndex: 'deleted_at',
      key: 'deleted_at',
      width: 155,
      render: (value) => <Text style={{ whiteSpace: 'nowrap' }}>{formatDateTimeVN(value)}</Text>,
    },
    {
      title: 'Loại dữ liệu',
      dataIndex: 'entity_type',
      key: 'entity_type',
      width: 145,
      render: (type) => {
        const conf = ENTITY_CONFIG[type] || { label: type, color: 'default' }
        return <Tag color={conf.color} style={{ fontWeight: 500 }}>{conf.label}</Tag>
      },
    },
    {
      title: 'Đối tượng đã xóa',
      key: 'title',
      width: 240,
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 600, color: '#0f172a' }}>{record.title || '—'}</div>
          <Text type="secondary" style={{ fontSize: 11 }}>
            ID: <code>{String(record.entity_id || '').slice(0, 18)}</code>
          </Text>
        </div>
      ),
    },
    {
      title: 'Lý do / Nguồn xóa',
      dataIndex: 'reason',
      key: 'reason',
      render: (reason) => <Text>{reason || '—'}</Text>,
    },
    {
      title: 'Người thực hiện',
      dataIndex: 'deleted_by',
      key: 'deleted_by',
      width: 190,
      render: (actor) => <Tag>{actor || 'Hệ thống'}</Tag>,
    },
    {
      title: 'Chi tiết',
      key: 'actions',
      width: 85,
      align: 'center',
      render: (_, record) => (
        <Button
          type="text"
          title="Xem dữ liệu trước khi xóa"
          icon={<EyeOutlined style={{ color: '#0284c7' }} />}
          onClick={() => setSelectedEntry(record)}
        />
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <Title level={3} style={{ margin: 0, color: '#0f172a' }}>
            <RestOutlined style={{ color: '#0284c7', marginRight: 8 }} />
            Lịch sử Dữ liệu Đã xóa
          </Title>
          <Text type="secondary">
            Theo dõi toàn bộ người dùng, thiết bị, phiên đăng ký (gồm phiên tự hoàn tất) và lịch sử truy cập đã bị xóa.
          </Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchHistory} loading={loading}>
            Tải lại
          </Button>
          {isSuperAdmin && items.length > 0 && (
            <Popconfirm
              title="Dọn sạch lịch sử đã xóa?"
              description="Thao tác này sẽ xóa toàn bộ danh sách nhật ký lưu trữ các mục đã xóa."
              onConfirm={handleClearHistory}
              okText="Xác nhận"
              cancelText="Hủy"
              okButtonProps={{ danger: true }}
            >
              <Button danger icon={<DeleteOutlined />}>
                Dọn sạch nhật ký
              </Button>
            </Popconfirm>
          )}
        </Space>
      </div>

      <Card
        size="small"
        style={{
          marginBottom: 16,
          background: 'linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%)',
          borderColor: '#bae6fd',
        }}
      >
        <Space wrap size="middle">
          <Select
            placeholder="Loại đối tượng"
            value={entityType}
            onChange={(val) => {
              setEntityType(val)
              setPage(1)
            }}
            style={{ width: 190 }}
            options={[
              { value: '', label: 'Tất cả loại dữ liệu' },
              { value: 'user', label: 'Người dùng đã xóa' },
              { value: 'device', label: 'Thiết bị đã xóa' },
              { value: 'session', label: 'Phiên đăng ký đã xóa' },
              { value: 'access_log', label: 'Lịch sử truy cập đã xóa' },
            ]}
          />

          <Input
            placeholder="Tìm theo tên, mã, lý do, người xóa..."
            prefix={<SearchOutlined style={{ color: '#0284c7' }} />}
            value={searchText}
            onChange={(e) => {
              setSearchText(e.target.value)
              setPage(1)
            }}
            style={{ width: 260 }}
            allowClear
          />

          <RangePicker
            value={timeRange}
            onChange={(vals) => {
              setTimeRange(vals)
              setPage(1)
            }}
            showTime={{ format: 'HH:mm' }}
            format="DD/MM/YYYY HH:mm"
            presets={rangePresets}
            placeholder={['Từ lúc xóa', 'Đến lúc xóa']}
            allowClear
            style={{ width: 310 }}
          />

          {hasActiveFilters && (
            <Button
              type="dashed"
              danger
              icon={<ClearOutlined />}
              onClick={() => {
                setEntityType('')
                setSearchText('')
                setTimeRange(null)
                setPage(1)
              }}
            >
              Xóa lọc
            </Button>
          )}

          <Tag color="cyan" style={{ fontWeight: 500 }}>
            Tổng cộng {total} mục đã xóa
          </Tag>
        </Space>
      </Card>

      <Card styles={{ body: { padding: 0 } }} style={{ borderColor: '#e0f2fe' }}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          tableLayout="fixed"
          className="centered-table-header"
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50'],
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps)
            },
            showTotal: (tot) => `Tổng số ${tot} bản ghi đã xóa`,
          }}
        />
      </Card>

      <Modal
        title="Chi tiết Dữ liệu Đã xóa"
        open={Boolean(selectedEntry)}
        onCancel={() => setSelectedEntry(null)}
        footer={<Button onClick={() => setSelectedEntry(null)}>Đóng</Button>}
        width={680}
      >
        {selectedEntry && (
          <Descriptions bordered column={1} size="small" style={{ marginTop: 12 }}>
            <Descriptions.Item label="Loại dữ liệu">
              <Tag color={ENTITY_CONFIG[selectedEntry.entity_type]?.color || 'default'}>
                {ENTITY_CONFIG[selectedEntry.entity_type]?.label || selectedEntry.entity_type}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Đối tượng">{selectedEntry.title}</Descriptions.Item>
            <Descriptions.Item label="ID gốc"><code>{selectedEntry.entity_id}</code></Descriptions.Item>
            <Descriptions.Item label="Lý do / Nguồn xóa">{selectedEntry.reason}</Descriptions.Item>
            <Descriptions.Item label="Người thực hiện">{selectedEntry.deleted_by}</Descriptions.Item>
            <Descriptions.Item label="Thời gian xóa">{formatDateTimeVN(selectedEntry.deleted_at)}</Descriptions.Item>
            <Descriptions.Item label="Dữ liệu gốc (Snapshot)">
              <pre
                style={{
                  margin: 0,
                  maxHeight: 280,
                  overflow: 'auto',
                  background: '#f8fafc',
                  padding: 10,
                  borderRadius: 6,
                  fontSize: 12,
                }}
              >
                {JSON.stringify(selectedEntry.snapshot, null, 2)}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

