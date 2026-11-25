import apiClient, { buildQueryString } from './apiClient.js'

export const deletionHistoryService = {
  /**
   * Lấy danh sách lịch sử các đối tượng đã bị xóa (người dùng, thiết bị, phiên, access log)
   * @param {{ limit?: number, offset?: number, entity_type?: string, search?: string, start_time?: string, end_time?: string }} params
   */
  async listHistory(params = {}) {
    const qs = buildQueryString(params)
    const { data } = await apiClient.request(`/deletion-history${qs}`)
    return data || { items: [], total: 0, has_more: false }
  },

  /**
   * Dọn sạch lịch sử đã xóa (chỉ dành cho Quản trị viên Cấp cao)
   */
  async clearHistory() {
    const { data } = await apiClient.request('/deletion-history', {
      method: 'DELETE',
    })
    return data || { cleared_count: 0 }
  },
}

export default deletionHistoryService

