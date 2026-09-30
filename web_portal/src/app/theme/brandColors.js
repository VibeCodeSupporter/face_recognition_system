/**
 * Bảng màu thương hiệu dùng cho phía JS (antd theme, chart, canvas...).
 * Nguồn sự thật cho CSS variables: src/app/styles/tokens.css
 * → khi đổi màu thương hiệu phải cập nhật cả 2 nơi.
 */
export const BRAND_COLORS = {
  primary: '#7c1dff',
  primaryHover: '#6614d9',
  primaryActive: '#4f0fae',
  primaryDark: '#a56bff',
  primaryDarkHover: '#c39bff',
  lightBackground: '#f6f5fb',
  darkBackground: '#121019',
}

/** Font stack dùng chung cho CSS và antd Design Token. */
export const FONT_FAMILY =
  "system-ui, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"

export default BRAND_COLORS
