import apiClient, { buildQueryString } from './apiClient.js'

export const logService = {
  /**
   * Lấy danh sách lịch sử truy cập phân trang (hỗ trợ lọc theo khoảng thời gian)
   * @param {{ limit?: number, offset?: number, user_id?: string, device_id?: string, result?: string, start_time?: string, end_time?: string }} params
   */
  async listLogs(params = {}) {
    const qs = buildQueryString(params)
    const { data } = await apiClient.request(`/access-logs${qs}`)
    return data || { items: [], total: 0, has_more: false }
  },

  /**
   * Truy xuất toàn bộ lịch sử truy cập khớp bộ lọc (phục vụ xuất báo cáo CSV)
   * @param {{ user_id?: string, device_id?: string, result?: string, start_time?: string, end_time?: string }} params
   */
  async exportAllLogs(params = {}, maxRows = 5000) {
    const allItems = []
    let offset = 0
    const limit = 100

    while (allItems.length < maxRows) {
      const data = await this.listLogs({ ...params, limit, offset })
      const items = data.items || []
      allItems.push(...items)
      if (!data.has_more || items.length === 0) {
        break
      }
      offset += items.length
    }

    return allItems.slice(0, maxRows)
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

  /**
   * Xóa lịch sử truy cập theo khoảng thời gian (chỉ dành cho Quản trị viên Cấp cao)
   * @param {{ start_time: string, end_time: string, result?: string, device_id?: string, user_id?: string }} params
   */
  async deleteLogsByRange(params = {}) {
    const qs = buildQueryString(params)
    const { data } = await apiClient.request(`/access-logs${qs}`, {
      method: 'DELETE',
    })
    return data || { deleted_count: 0 }
  },
}

export default logService
