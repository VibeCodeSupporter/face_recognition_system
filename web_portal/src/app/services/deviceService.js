import apiClient, { buildQueryString } from './apiClient.js'

export const deviceService = {
  /**
   * Lấy danh sách thiết bị phân trang
   * @param {{ limit?: number, offset?: number, status?: string, device_code?: string }} params
   */
  async listDevices(params = {}) {
    const qs = buildQueryString(params)
    const { data } = await apiClient.request(`/devices${qs}`)
    return data || { items: [], total: 0, has_more: false }
  },

  /**
   * Lấy toàn bộ thiết bị phục vụ làm lookup (ghép bảng và hiển thị trong select box)
   */
  async listAllDevices() {
    const items = []
    let offset = 0
    const limit = 100

    while (true) {
      const data = await this.listDevices({ limit, offset })
      const currentItems = data.items || []
      items.push(...currentItems)

      if (!data.has_more || currentItems.length === 0 || offset >= 100000) {
        break
      }
      offset += currentItems.length
    }

    return items
  },

  /**
   * Lấy chi tiết một thiết bị theo ID
   */
  async getDevice(id) {
    const { data } = await apiClient.request(`/devices/${id}`)
    return data
  },

  /**
   * Tạo thiết bị mới (trả về dữ liệu kèm device_token bảo mật dùng một lần)
   * @param {{ device_code: string, name: string, location?: string, status?: string, settings: { threshold: number, doorDuration: number, liveness: boolean } }} payload
   */
  async createDevice(payload) {
    const { data } = await apiClient.request('/devices', {
      method: 'POST',
      body: payload,
    })
    return data
  },

  /**
   * Cập nhật thông tin và cấu hình thiết bị
   */
  async updateDevice(id, payload) {
    const { data } = await apiClient.request(`/devices/${id}`, {
      method: 'PATCH',
      body: payload,
    })
    return data
  },

  /**
   * Xóa thiết bị
   */
  async deleteDevice(id) {
    await apiClient.request(`/devices/${id}`, {
      method: 'DELETE',
    })
    return true
  },
}

export default deviceService

