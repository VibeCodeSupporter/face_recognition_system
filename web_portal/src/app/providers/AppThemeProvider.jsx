import { useMemo } from 'react'
import { App as AntdApp, ConfigProvider } from 'antd'
import usePrefersDarkMode from '../hooks/usePrefersDarkMode.js'
import createAntdTheme from '../theme/antdTheme.js'

/**
 * Bọc toàn bộ ứng dụng bằng ConfigProvider (design token của antd) và
 * antd App (cung cấp context cho message/notification/modal).
 *
 * @param {{ children: React.ReactNode }} props
 */
export default function AppThemeProvider({ children }) {
  const isDarkMode = usePrefersDarkMode()
  const themeConfig = useMemo(() => createAntdTheme(isDarkMode), [isDarkMode])

  return (
    <ConfigProvider theme={themeConfig}>
      <AntdApp>{children}</AntdApp>
    </ConfigProvider>
  )
}
