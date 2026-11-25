import apiClient, { ApiError } from './apiClient.js'

export const authService = {
  /**
   * Đăng nhập với username và password quản trị viên
   */
  async login(username, password) {
    const { data } = await apiClient.request('/auth/login', {
      method: 'POST',
      body: { username, password },
    })
    apiClient.setToken(data.token, data.admin)
    return data
  },

  /**
   * Đăng xuất hệ thống
   */
  async logout() {
    try {
      if (apiClient.token) {
        await apiClient.request('/auth/logout', { method: 'POST' })
      }
    } catch (_) {
      // bỏ qua lỗi backend khi logout
    } finally {
      apiClient.clearAuth()
    }
  },

  /**
   * Kiểm tra phiên đăng nhập hiện tại bằng token đã lưu
   */
  async checkSession() {
    if (!apiClient.token) {
      if (apiClient.key) {
        // Kiểm tra health nếu dùng api key
        return await this.verifyApiKey(apiClient.key)
      }
      return false
    }

    try {
      const { data } = await apiClient.request('/auth/me', { token: apiClient.token })
      apiClient.setToken(apiClient.token, data)
      return true
    } catch (_) {
      apiClient.clearAuth()
      return false
    }
  },

  /**
   * Kết nối bằng backend API Key (x-api-key)
   */
  async verifyApiKey(key) {
    if (!key || !/^[A-Za-z0-9_-]{32,256}$/.test(key.trim())) {
      throw new ApiError(
        'Backend API Key không đúng định dạng (32-256 ký tự chữ, số, gạch dưới hoặc gạch ngang).',
        400,
        'INVALID_API_KEY'
      )
    }

    await apiClient.request('/health', { key: key.trim() })
    apiClient.setApiKey(key.trim())
    return true
  },

  getCurrentUser() {
    return apiClient.admin
  },

  /**
   * Cập nhật thông tin quản trị viên hiện tại
   */
  async updateProfile(payload) {
    const { data } = await apiClient.request('/auth/profile', {
      method: 'PATCH',
      body: payload,
    })
    apiClient.admin = data
    try {
      sessionStorage.setItem('faceaccess_admin', JSON.stringify(data))
    } catch (_) {}
    return data
  },

  isAuthenticated() {
    return apiClient.isAuthenticated()
  },

  getAuthType() {
    return apiClient.getAuthType()
  },
}

export default authService

