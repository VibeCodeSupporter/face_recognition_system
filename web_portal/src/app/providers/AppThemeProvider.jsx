import { useMemo } from 'react'
import { App as AntdApp, ConfigProvider } from 'antd'
import createAntdTheme from '../theme/antdTheme.js'

/**
 * Cung cấp Ant Design Theme chuẩn Light sáng sủa, rực rỡ,
 * cố định màu sắc hài hòa Xanh da trời & Vàng ấm, không bị biến đổi
 * hay xung đột khi hệ điều hành máy tính bật Dark Mode.
 *
 * @param {{ children: React.ReactNode }} props
 */
export default function AppThemeProvider({ children }) {
  // Cố định theme sáng sủa, rõ nét, loại bỏ lỗi chữ trắng nền trắng
  const themeConfig = useMemo(() => createAntdTheme(false), [])

  return (
    <ConfigProvider theme={themeConfig}>
      <AntdApp>{children}</AntdApp>
    </ConfigProvider>
  )
}
