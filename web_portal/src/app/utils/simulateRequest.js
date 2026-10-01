/** Thời gian giả lập phản hồi của backend (ms). */
const SIMULATED_LATENCY_MS = 700

/**
 * Giả lập một request tới Backend Server (Cloud) khi backend chưa sẵn sàng.
 * Nhờ vậy UI có thể demo đầy đủ trạng thái `loading`/`success` mà chưa cần API.
 *
 * TODO(api): thay bằng tầng services/api khi Backend Server được triển khai.
 *
 * @param {object} [payload] - dữ liệu submit (hiện chỉ dùng cho log/devtools)
 * @returns {Promise<{ ok: true, payload: object }>}
 */
export default function simulateRequest(payload = {}) {
  return new Promise((resolve) => {
    setTimeout(() => resolve({ ok: true, payload }), SIMULATED_LATENCY_MS)
  })
}
