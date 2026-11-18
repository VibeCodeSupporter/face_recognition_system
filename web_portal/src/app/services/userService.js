import apiClient, { buildQueryString } from './apiClient.js'

export const userService = {
  /**
   * Lấy danh sách tất cả người dùng
   * @param {{ status?: string, department?: string }} filters
   */
  async listUsers(filters = {}) {
    const qs = buildQueryString(filters)
    const { data } = await apiClient.request(`/users${qs}`)
    return data || []
  },

  /**
   * Lấy thông tin chi tiết một người dùng theo ID
   */
  async getUser(id) {
    const { data } = await apiClient.request(`/users/${id}`)
    return data
  },

  /**
   * Tạo người dùng mới
   * @param {{ user_code: string, full_name: string, email?: string, phone?: string, department?: string, role?: string, status?: string }} payload
   */
  async createUser(payload) {
    const { data } = await apiClient.request('/users', {
      method: 'POST',
      body: payload,
    })
    return data
  },

  /**
   * Cập nhật thông tin người dùng
   */
  async updateUser(id, payload) {
    const { data } = await apiClient.request(`/users/${id}`, {
      method: 'PATCH',
      body: payload,
    })
    return data
  },

  /**
   * Xóa người dùng
   */
  async deleteUser(id) {
    await apiClient.request(`/users/${id}`, {
      method: 'DELETE',
    })
    return true
  },

  /**
   * Lấy vector khuôn mặt của người dùng
   */
  async getFaceEmbedding(userId) {
    try {
      const { data } = await apiClient.request(`/users/${userId}/face-embedding`)
      return data
    } catch (error) {
      if (error.status === 404) {
        return null // Chưa có vector
      }
      throw error
    }
  },

  /**
   * Lưu hoặc cập nhật vector khuôn mặt
   * @param {string} userId
   * @param {{ model_name: string, model_version: string, dimension: number, image_url?: string, embedding_data: number[] }} payload
   */
  async saveFaceEmbedding(userId, payload) {
    const { data } = await apiClient.request(`/users/${userId}/face-embedding`, {
      method: 'PUT',
      body: payload,
    })
    return data
  },

  /**
   * Xóa vector khuôn mặt của người dùng
   */
  async deleteFaceEmbedding(userId) {
    await apiClient.request(`/users/${userId}/face-embedding`, {
      method: 'DELETE',
    })
    return true
  },
}

export default userService

