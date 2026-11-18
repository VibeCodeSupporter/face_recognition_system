import apiClient, { buildQueryString } from './apiClient.js'

export const logService = {
  /**
   * Lấy danh sách lịch sử truy cập phân trang
   * @param {{ limit?: number, offset?: number, user_id?: string, device_id?: string, result?: string }} params
   */
  async listLogs(params = {}) {
    const qs = buildQueryString(params)
    const { data } = await apiClient.request(`/access-logs${qs}`)
    return data || { items: [], total: 0, has_more: false }
  },

  /**
   * Lấy chi tiết một sự kiện truy cập theo ID
   */
  async getLog(id) {
    const { data } = await apiClient.request(`/access-logs/${id}`)
    return data
  },

  /**
   * Ghi sự kiện truy cập mới (hỗ trợ kiểm tra idempotency của backend)
   * @param {{ id: string, device_id: string, user_id?: string|null, result: 'granted'|'denied', confidence?: number|null, access_time: string }} payload
   */
  async createLog(payload) {
    const { data, status } = await apiClient.request('/access-logs', {
      method: 'POST',
      body: payload,
    })
    return { data, isCreated: status === 201 }
  },
}

export default logService

