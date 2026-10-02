import { useEffect, useState } from 'react'

const DARK_MODE_QUERY = '(prefers-color-scheme: dark)'

function readPrefersDarkMode() {
  return window.matchMedia(DARK_MODE_QUERY).matches
}

/**
 * Theo dõi thiết lập dark mode của hệ điều hành/trình duyệt.
 * Được AppThemeProvider dùng để chuyển antd theme theo thời gian thực.
 *
 * @returns {boolean} true khi giao diện nên dùng dark mode
 */
export default function usePrefersDarkMode() {
  const [isDarkMode, setIsDarkMode] = useState(readPrefersDarkMode)

  useEffect(() => {
    const mediaQueryList = window.matchMedia(DARK_MODE_QUERY)
    const handleChange = (event) => setIsDarkMode(event.matches)

    setIsDarkMode(mediaQueryList.matches)
    mediaQueryList.addEventListener('change', handleChange)
    return () => mediaQueryList.removeEventListener('change', handleChange)
  }, [])

  return isDarkMode
}
