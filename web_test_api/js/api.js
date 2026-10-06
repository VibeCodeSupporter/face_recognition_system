'use strict';

class ApiError extends Error {
  constructor(message, status = 0, code = 'NETWORK_ERROR', details = [], requestId = '') {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

const ERROR_MESSAGES = {
  UNAUTHORIZED: 'API key không đúng hoặc đã thay đổi. Hãy kết nối lại.',
  NOT_FOUND: 'Bản ghi không còn tồn tại. Hãy tải lại danh sách.',
  DUPLICATE: 'Mã này đã tồn tại. Vui lòng dùng mã khác.',
  REFERENCE_CONFLICT: 'Không thể thực hiện vì bản ghi đang được tham chiếu hoặc liên kết không còn tồn tại.',
  USER_INACTIVE: 'Người dùng đã ngừng hoạt động, không thể tạo phiên đăng ký.',
  FACE_REQUIRED: 'Cần lưu vector khuôn mặt trước khi hoàn tất phiên đăng ký.',
  SESSION_NOT_PENDING: 'Phiên đã hết hạn hoặc đã kết thúc. Hãy tải lại danh sách.',
  LOG_ID_CONFLICT: 'Mã sự kiện đã tồn tại với nội dung khác. Không thể ghi đè lịch sử.',
  CONSTRAINT_VIOLATION: 'Dữ liệu không đáp ứng ràng buộc database.',
  REQUIRED_FIELD: 'Thiếu trường bắt buộc trong database.',
  VALUE_TOO_LONG: 'Một trường vượt quá độ dài database cho phép.',
  BODY_TOO_LARGE: 'Dữ liệu vượt quá 128 KB.',
  DATABASE_UNAVAILABLE: 'Không truy cập được database. Kiểm tra backend rồi thử lại.',
  INTERNAL_ERROR: 'Backend gặp lỗi. Hãy kiểm tra bằng mã request bên dưới.',
  INVALID_JSON: 'Nội dung JSON không hợp lệ.',
  VALIDATION_ERROR: 'Dữ liệu nhập chưa hợp lệ. Kiểm tra các trường được đánh dấu.',
};

const Api = {
  key: '',
  onUnauthorized: () => {},
  async request(path, { method = 'GET', body, key = this.key, signal } = {}) {
    if (!key) throw new ApiError(ERROR_MESSAGES.UNAUTHORIZED, 401, 'UNAUTHORIZED');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 30000);
    const abort = () => controller.abort();
    signal?.addEventListener('abort', abort, { once: true });
    if (signal?.aborted) controller.abort();
    try {
      const encoded = body === undefined ? undefined : JSON.stringify(body);
      if (encoded && new TextEncoder().encode(encoded).length > 128 * 1024) {
        throw new ApiError(ERROR_MESSAGES.BODY_TOO_LARGE, 413, 'BODY_TOO_LARGE');
      }
      const response = await fetch(`/api/v1${path}`, {
        method, signal: controller.signal, cache: 'no-store', credentials: 'omit', redirect: 'error',
        headers: { 'x-api-key': key, ...(encoded === undefined ? {} : { 'Content-Type': 'application/json' }) },
        body: encoded,
      });
      const text = response.status === 204 ? '' : await response.text();
      let payload;
      try { payload = text ? JSON.parse(text) : null; }
      catch { throw new ApiError('Backend trả dữ liệu không hợp lệ. Kiểm tra địa chỉ và proxy.', response.status, 'INVALID_RESPONSE'); }
      if (!response.ok) {
        const error = payload?.error || {};
        if (response.status === 401 && key === this.key) this.onUnauthorized();
        throw new ApiError(ERROR_MESSAGES[error.code] || `Request thất bại (HTTP ${response.status}).`,
          response.status, error.code || 'HTTP_ERROR', error.details || payload?.detail || [], error.request_id || '');
      }
      if (response.status !== 204 && (!payload || !Object.hasOwn(payload, 'data'))) {
        throw new ApiError('Response thiếu trường data. Kiểm tra hợp đồng API.', response.status, 'INVALID_RESPONSE');
      }
      return { data: payload?.data, status: response.status };
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (signal?.aborted) throw new ApiError('Request đã hủy.', 0, 'CANCELLED');
      throw new ApiError('Không nhận được phản hồi từ backend. Kiểm tra kết nối; nếu vừa lưu, hãy tải lại để xác nhận trước khi gửi lại.');
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener('abort', abort);
    }
  },
};

function queryString(values) {
  const params = new URLSearchParams();
  for (const [name, value] of Object.entries(values)) {
    if (value !== '' && value !== undefined && value !== null) params.set(name, String(value));
  }
  return params.size ? `?${params}` : '';
}

function errorText(error) {
  let message = error.message;
  for (const detail of error.details || []) {
    const path = detail.path || (detail.loc || []).join('.');
    message += `\n${path}: ${detail.message || detail.msg || 'Dữ liệu không hợp lệ'}`;
  }
  if (error.requestId) message += `\nRequest ID: ${error.requestId}`;
  return Api.key ? message.split(Api.key).join('[đã ẩn]') : message;
}
