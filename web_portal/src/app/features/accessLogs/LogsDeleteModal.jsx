import { useMemo, useState } from 'react'
import { DeleteOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  DatePicker,
  Form,
  Modal,
  Popconfirm,
  Segmented,
  Select,
  Typography,
} from 'antd'
import dayjs from 'dayjs'
import logService from '../../services/logService.js'
import { getErrorMessage } from '../../services/apiClient.js'

const { Text } = Typography
const { RangePicker } = DatePicker

function computeRangeFromMode(mode, singleValue, customRange) {
  if (mode === 'range') {
    if (!Array.isArray(customRange) || !customRange[0] || !customRange[1]) {
      return null
    }
    const [start, end] = customRange
    return {
      start_time: `${start.format('YYYY-MM-DD[T]HH:mm:ss')}.000+07:00`,
      end_time: `${end.format('YYYY-MM-DD[T]HH:mm:ss')}.999+07:00`,
      label: `từ ${start.format('HH:mm:ss DD/MM/YYYY')} đến ${end.format('HH:mm:ss DD/MM/YYYY')}`,
    }
  }

  if (!singleValue) return null

  if (mode === 'hour') {
    const prefix = singleValue.format('YYYY-MM-DD[T]HH')
    return {
      start_time: `${prefix}:00:00.000+07:00`,
      end_time: `${prefix}:59:59.999+07:00`,
      label: `khung giờ ${singleValue.format('HH')}:00:00 – ${singleValue.format('HH')}:59:59 ngày ${singleValue.format('DD/MM/YYYY')}`,
    }
  }

  if (mode === 'day') {
    const datePrefix = singleValue.format('YYYY-MM-DD')
    return {
      start_time: `${datePrefix}T00:00:00.000+07:00`,
      end_time: `${datePrefix}T23:59:59.999+07:00`,
      label: `cả ngày ${singleValue.format('DD/MM/YYYY')} (00:00:00 – 23:59:59)`,
    }
  }

  if (mode === 'month') {
    const monthPrefix = singleValue.format('YYYY-MM')
    const lastDay = singleValue.endOf('month').format('DD')
    return {
      start_time: `${monthPrefix}-01T00:00:00.000+07:00`,
      end_time: `${monthPrefix}-${lastDay}T23:59:59.999+07:00`,
      label: `cả tháng ${singleValue.format('MM/YYYY')} (01/${singleValue.format('MM')} – ${lastDay}/${singleValue.format('MM')})`,
    }
  }

  return null
}

export default function LogsDeleteModal({ open, devices = [], onClose, onDeleted }) {
  const { message } = AntdApp.useApp()

  const [mode, setMode] = useState('day')
  const [singleValue, setSingleValue] = useState(() => dayjs())
  const [customRange, setCustomRange] = useState(() => [dayjs().startOf('hour'), dayjs()])
  const [resultFilter, setResultFilter] = useState('')
  const [deviceFilter, setDeviceFilter] = useState('')
  const [deleting, setDeleting] = useState(false)

  const computed = useMemo(
    () => computeRangeFromMode(mode, singleValue, customRange),
    [mode, singleValue, customRange]
  )

  const handleConfirmDelete = async () => {
    if (!computed) {
      message.warning('Vui lòng chọn thời gian cần xóa!')
      return
    }
    setDeleting(true)
    try {
      const params = {
        start_time: computed.start_time,
        end_time: computed.end_time,
        ...(resultFilter ? { result: resultFilter } : {}),
        ...(deviceFilter ? { device_id: deviceFilter } : {}),
      }
      const res = await logService.deleteLogsByRange(params)
      const count = res?.deleted_count ?? 0
      if (count > 0) {
        message.success(`Đã xóa vĩnh viễn ${count} bản ghi lịch sử truy cập!`)
      } else {
        message.info('Không có bản ghi lịch sử nào trong khoảng thời gian đã chọn.')
      }
      onDeleted?.()
      onClose()
    } catch (error) {
      message.error(getErrorMessage(error))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#dc2626' }}>
          <DeleteOutlined />
          <span>Xóa Lịch sử Truy cập</span>
        </div>
      }
      open={open}
      onCancel={onClose}
      width={560}
      destroyOnClose
      footer={[
        <Button key="cancel" onClick={onClose} disabled={deleting}>
          Hủy
        </Button>,
        <Popconfirm
          key="confirm"
          title="Xác nhận xóa vĩnh viễn lịch sử?"
          description={
            computed
              ? `Dữ liệu truy cập trong ${computed.label} sẽ bị xóa vĩnh viễn khỏi cơ sở dữ liệu.`
              : 'Vui lòng chọn thời gian hợp lệ.'
          }
          onConfirm={handleConfirmDelete}
          okText="Xóa vĩnh viễn"
          cancelText="Quay lại"
          okButtonProps={{ danger: true, loading: deleting }}
          disabled={!computed}
        >
          <Button
            type="primary"
            danger
            icon={<DeleteOutlined />}
            loading={deleting}
            disabled={!computed}
          >
            Xóa lịch sử
          </Button>
        </Popconfirm>,
      ]}
    >
      <Form layout="vertical" style={{ marginTop: 12 }}>
        <Form.Item label="Chế độ xóa theo thời gian">
          <Segmented
            block
            value={mode}
            onChange={(val) => setMode(val)}
            options={[
              { value: 'hour', label: 'Theo giờ' },
              { value: 'day', label: 'Theo ngày' },
              { value: 'month', label: 'Theo tháng' },
              { value: 'range', label: 'Khoảng tùy chọn' },
            ]}
          />
        </Form.Item>

        {mode === 'hour' && (
          <Form.Item
            label="Chọn Ngày và Giờ cần xóa"
            extra="Sẽ xóa toàn bộ lượt truy cập xảy ra trong giờ đã chọn (phút 00 đến 59)."
          >
            <DatePicker
              value={singleValue}
              onChange={(val) => setSingleValue(val)}
              showTime={{ format: 'HH' }}
              format="HH:00 · DD/MM/YYYY"
              style={{ width: '100%' }}
              placeholder="Chọn ngày và giờ..."
            />
          </Form.Item>
        )}

        {mode === 'day' && (
          <Form.Item
            label="Chọn Ngày cần xóa"
            extra="Sẽ xóa toàn bộ lượt truy cập trong suốt 24 giờ của ngày đã chọn."
          >
            <DatePicker
              value={singleValue}
              onChange={(val) => setSingleValue(val)}
              format="DD/MM/YYYY"
              style={{ width: '100%' }}
              placeholder="Chọn ngày..."
            />
          </Form.Item>
        )}

        {mode === 'month' && (
          <Form.Item
            label="Chọn Tháng cần xóa"
            extra="Sẽ xóa toàn bộ lượt truy cập từ ngày đầu tiên đến ngày cuối cùng của tháng."
          >
            <DatePicker
              picker="month"
              value={singleValue}
              onChange={(val) => setSingleValue(val)}
              format="MM/YYYY"
              style={{ width: '100%' }}
              placeholder="Chọn tháng..."
            />
          </Form.Item>
        )}

        {mode === 'range' && (
          <Form.Item
            label="Chọn khoảng thời gian cần xóa"
            extra="Sẽ xóa toàn bộ lượt truy cập nằm giữa 2 mốc thời gian đã chọn."
          >
            <RangePicker
              value={customRange}
              onChange={(vals) => setCustomRange(vals)}
              showTime={{ format: 'HH:mm:ss' }}
              format="DD/MM/YYYY HH:mm:ss"
              style={{ width: '100%' }}
            />
          </Form.Item>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Form.Item label="Lọc kết quả cần xóa (tùy chọn)">
            <Select
              value={resultFilter}
              onChange={setResultFilter}
              options={[
                { value: '', label: 'Tất cả kết quả (Cho phép & Từ chối)' },
                { value: 'denied', label: 'Chỉ xóa lượt Từ chối' },
                { value: 'granted', label: 'Chỉ xóa lượt Cho phép' },
              ]}
            />
          </Form.Item>

          <Form.Item label="Lọc thiết bị (tùy chọn)">
            <Select
              value={deviceFilter}
              onChange={setDeviceFilter}
              showSearch
              optionFilterProp="label"
              options={[
                { value: '', label: 'Tất cả thiết bị' },
                ...devices.map((d) => ({ value: d.id, label: `${d.name} (${d.device_code})` })),
              ]}
            />
          </Form.Item>
        </div>

        <Alert
          type="warning"
          showIcon
          icon={<ExclamationCircleOutlined />}
          title="Lưu ý thao tác không thể hoàn tác"
          description={
            computed ? (
              <Text>
                Hệ thống sẽ xóa dữ liệu truy cập trong <strong>{computed.label}</strong> (Giờ Việt Nam UTC+7).
              </Text>
            ) : (
              'Vui lòng chọn thời gian hợp lệ để xem trước phạm vi xóa.'
            )
          }
        />
      </Form>
    </Modal>
  )
}

