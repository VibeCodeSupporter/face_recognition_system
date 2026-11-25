/**
 * FaceAccess API Client
 * Kết nối với backend FastAPI (http://127.0.0.1:5000/api/v1).
 * Hỗ trợ xác thực qua Bearer Token (JWT quản trị) và x-api-key (Developer).
 */

export class ApiError extends Error {
  constructor(message, status = 0, code = 'NETWORK_ERROR', details = [], requestId = '') {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.requestId = requestId
  }
}

export const ERROR_MESSAGES = {
  UNAUTHORIZED: 'API key hoặc phiên đăng nhập không đúng hoặc đã hết hạn. Hãy đăng nhập lại.',
  NOT_FOUND: 'Bản ghi không tồn tại hoặc đã bị xóa. Hãy tải lại danh sách.',
  DUPLICATE: 'Mã này đã tồn tại trong hệ thống. Vui lòng chọn mã khác.',
  REFERENCE_CONFLICT: 'Không thể thực hiện vì bản ghi đang được tham chiếu hoặc dữ liệu liên kết không tồn tại.',
  USER_INACTIVE: 'Người dùng đã ngừng hoạt động, không thể tạo phiên đăng ký.',
  USER_ALREADY_REGISTERED: 'Người dùng này đã đăng ký khuôn mặt trong hệ thống. Không thể tạo phiên đăng ký mới.',
  USER_HAS_PENDING_SESSION: 'Người dùng này hiện đã có một phiên đăng ký đang chờ xử lý.',
  DEVICE_QUEUE_FULL: 'Thiết bị đã đạt tối đa 10 phiên chờ đăng ký. Vui lòng đợi hoàn tất các phiên trước.',
  FACE_REQUIRED: 'Cần lưu vector khuôn mặt trước khi hoàn tất phiên đăng ký.',
  SESSION_NOT_PENDING: 'Phiên đã hết hạn hoặc đã kết thúc. Hãy tải lại danh sách.',
  LOG_ID_CONFLICT: 'Mã sự kiện (UUID) đã tồn tại với nội dung khác. Không thể ghi đè lịch sử.',
  CONSTRAINT_VIOLATION: 'Dữ liệu không đáp ứng ràng buộc cơ sở dữ liệu.',
  REQUIRED_FIELD: 'Thiếu trường bắt buộc trong dữ liệu gửi lên.',
  VALUE_TOO_LONG: 'Một trường dữ liệu vượt quá độ dài cho phép.',
  BODY_TOO_LARGE: 'Dữ liệu gửi lên vượt quá giới hạn 128 KB.',
  DATABASE_UNAVAILABLE: 'Không kết nối được cơ sở dữ liệu Supabase. Vui lòng kiểm tra backend.',
  INTERNAL_ERROR: 'Máy chủ backend gặp sự cố nội bộ. Vui lòng kiểm tra lại cấu hình.',
  INVALID_JSON: 'Nội dung JSON gửi lên không hợp lệ.',
  VALIDATION_ERROR: 'Dữ liệu nhập chưa hợp lệ. Vui lòng kiểm tra các trường được đánh dấu.',
  INVALID_CREDENTIALS: 'Tên đăng nhập hoặc mật khẩu không chính xác. Vui lòng thử lại.',
}

const STORAGE_KEY_TOKEN = 'faceaccess_token'
const STORAGE_KEY_KEY = 'faceaccess_api_key'
const STORAGE_KEY_ADMIN = 'faceaccess_admin'

class ApiClient {
  constructor() {
    this.token = ''
    this.key = ''
    this.admin = null
    this.onUnauthorizedCallbacks = new Set()

    // Khôi phục phiên làm việc từ sessionStorage nếu có
    try {
      this.token = sessionStorage.getItem(STORAGE_KEY_TOKEN) || ''
      this.key = sessionStorage.getItem(STORAGE_KEY_KEY) || ''
      const storedAdmin = sessionStorage.getItem(STORAGE_KEY_ADMIN)
      if (storedAdmin) {
        this.admin = JSON.parse(storedAdmin)
      }
    } catch (_) {
      // bỏ qua lỗi nếu storage bị chặn
    }
  }

  isAuthenticated() {
    return Boolean(this.token || this.key)
  }

  getAuthType() {
    if (this.token) return 'token'
    if (this.key) return 'key'
    return null
  }

  onUnauthorized(callback) {
    this.onUnauthorizedCallbacks.add(callback)
    return () => this.onUnauthorizedCallbacks.delete(callback)
  }

  notifyUnauthorized() {
    for (const callback of this.onUnauthorizedCallbacks) {
      try {
        callback()
      } catch (_) { }
    }
  }

  setToken(token, adminInfo = null) {
    this.token = token || ''
    this.key = ''
    this.admin = adminInfo
    try {
      if (token) {
        sessionStorage.setItem(STORAGE_KEY_TOKEN, token)
        sessionStorage.removeItem(STORAGE_KEY_KEY)
        if (adminInfo) {
          sessionStorage.setItem(STORAGE_KEY_ADMIN, JSON.stringify(adminInfo))
        }
      } else {
        sessionStorage.removeItem(STORAGE_KEY_TOKEN)
        sessionStorage.removeItem(STORAGE_KEY_ADMIN)
      }
    } catch (_) { }
  }

  setApiKey(key) {
    this.key = key || ''
    this.token = ''
    this.admin = null
    try {
      if (key) {
        sessionStorage.setItem(STORAGE_KEY_KEY, key)
        sessionStorage.removeItem(STORAGE_KEY_TOKEN)
        sessionStorage.removeItem(STORAGE_KEY_ADMIN)
      } else {
        sessionStorage.removeItem(STORAGE_KEY_KEY)
      }
    } catch (_) { }
  }

  clearAuth() {
    this.token = ''
    this.key = ''
    this.admin = null
    try {
      sessionStorage.removeItem(STORAGE_KEY_TOKEN)
      sessionStorage.removeItem(STORAGE_KEY_KEY)
      sessionStorage.removeItem(STORAGE_KEY_ADMIN)
    } catch (_) { }
  }

  async request(path, { method = 'GET', body, key = this.key, token = this.token, signal } = {}) {
    const isPublic = path === '/auth/login'
    if (!isPublic && !key && !token) {
      throw new ApiError(ERROR_MESSAGES.UNAUTHORIZED, 401, 'UNAUTHORIZED')
    }

    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 30000)
    const abortHandler = () => controller.abort()

    if (signal) {
      signal.addEventListener('abort', abortHandler, { once: true })
      if (signal.aborted) controller.abort()
    }

    try {
      const encodedBody = body === undefined ? undefined : JSON.stringify(body)
      if (encodedBody && new TextEncoder().encode(encodedBody).length > 128 * 1024) {
        throw new ApiError(ERROR_MESSAGES.BODY_TOO_LARGE, 413, 'BODY_TOO_LARGE')
      }

      const headers = {
        ...(encodedBody !== undefined ? { 'Content-Type': 'application/json' } : {}),
      }

      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      } else if (key) {
        headers['x-api-key'] = key
      }

      const response = await fetch(`/api/v1${path}`, {
        method,
        signal: controller.signal,
        cache: 'no-store',
        credentials: 'omit',
        redirect: 'error',
        headers,
        body: encodedBody,
      })

      const text = response.status === 204 ? '' : await response.text()
      let payload = null

      if (text) {
        try {
          payload = JSON.parse(text)
        } catch {
          throw new ApiError(
            'Backend trả về định dạng phản hồi không hợp lệ.',
            response.status,
            'INVALID_RESPONSE'
          )
        }
      }

      if (!response.ok) {
        const error = payload?.error || {}
        if (response.status === 401 && !isPublic) {
          this.notifyUnauthorized()
        }
          let friendlyMessage =
            ERROR_MESSAGES[error.code] ||
        error.message

        if (!friendlyMessage) {
          if (response.status === 502 || response.status === 504) {
            friendlyMessage =
              'Không thể kết nối đến máy chủ Backend (HTTP 502 Bad Gateway). Vui lòng khởi động backend Python (chạy: python run.py trong thư mục backend).'
          } else if (response.status === 503) {
            friendlyMessage =
              'Máy chủ Backend tạm thời không khả dụng (HTTP 503 Service Unavailable).'
          } else {
            friendlyMessage = `Yêu cầu thất bại (HTTP ${response.status}).`
          }
        }
        throw new ApiError(
          friendlyMessage,
          response.status,
          error.code || 'HTTP_ERROR',
          error.details || payload?.detail || [],
          error.request_id || ''
        )
      }

      if (response.status !== 204 && (!payload || !Object.hasOwn(payload, 'data'))) {
        throw new ApiError(
          'Dữ liệu phản hồi thiếu trường "data". Kiểm tra giao thức API.',
          response.status,
          'INVALID_RESPONSE'
        )
      }

      return { data: payload?.data, status: response.status }
    } catch (err) {
      if (err instanceof ApiError) throw err
      if (signal?.aborted || err.name === 'AbortError') {
        throw new ApiError('Yêu cầu đã bị hủy hoặc quá thời gian chờ (30 giây).', 0, 'CANCELLED')
      }
      throw new ApiError(
        'Không thể kết nối đến Backend máy chủ. Vui lòng kiểm tra backend (http://127.0.0.1:5000) đã được khởi chạy chưa.'
      )
    } finally {
      clearTimeout(timer)
      if (signal) {
        signal.removeEventListener('abort', abortHandler)
      }
    }
  }
}

export const apiClient = new ApiClient()
export default apiClient

/**
 * Định dạng chuỗi ngày giờ ISO thành chuỗi giờ Việt Nam (UTC+7)
 */
export function formatDateTimeVN(isoString) {
  if (!isoString) return '—'
  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date)
}

/**
 * Chuyển đổi đối tượng query param thành chuỗi query string
 */
export function buildQueryString(params = {}) {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value))
    }
  }
  const str = searchParams.toString()
  return str ? `?${str}` : ''
}

/**
 * Trích xuất thông báo lỗi chi tiết dạng chuỗi
 */
export function getErrorMessage(error) {
  if (!error) return 'Đã có lỗi xảy ra.'
  let message = error.message || 'Lỗi không xác định'
  if (Array.isArray(error.details) && error.details.length > 0) {
    const detailsText = error.details
      .map((item) => {
        const path = item.path || (item.loc || []).join('.')
        return path ? `${path}: ${item.message || item.msg || 'Không hợp lệ'}` : item.message || item.msg
      })
      .filter(Boolean)
      .join('\n')
    if (detailsText) {
      message += `\n${detailsText}`
    }
  }
  if (error.requestId) {
    message += `\n(Mã yêu cầu: ${error.requestId})`
  }
  return message
}

