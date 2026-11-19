import apiClient, { buildQueryString } from './apiClient.js'

export const sessionService = {
  /**
   * Lấy danh sách phiên đăng ký phân trang
   * @param {{ limit?: number, offset?: number, user_id?: string, device_id?: string, status?: string }} params
   */
  async listSessions(params = {}) {
    const qs = buildQueryString(params)
    const { data } = await apiClient.request(`/registration-sessions${qs}`)
    return data || { items: [], total: 0, has_more: false }
  },

  /**
   * Lấy chi tiết phiên đăng ký theo ID
   */
  async getSession(id) {
    const { data } = await apiClient.request(`/registration-sessions/${id}`)
    return data
  },

  /**
   * Tạo phiên đăng ký mới
   * @param {{ user_id: string, device_id: string, expires_at?: string }} payload
   */
  async createSession(payload) {
    const { data } = await apiClient.request('/registration-sessions', {
      method: 'POST',
      body: payload,
    })
    return data
  },

  /**
   * Cập nhật trạng thái phiên đăng ký ('completed' | 'cancelled' | 'failed')
   */
  async updateStatus(id, status) {
    const { data } = await apiClient.request(`/registration-sessions/${id}`, {
      method: 'PATCH',
      body: { status },
    })
    return data
  },

  /**
   * Xóa phiên đăng ký
   */
  async deleteSession(id) {
    await apiClient.request(`/registration-sessions/${id}`, {
      method: 'DELETE',
    })
    return true
  },
}

export default sessionService

