import { theme as antdTheme } from 'antd'
import { BRAND_COLORS, FONT_FAMILY } from './brandColors.js'

/**
 * Sinh cấu hình theme cho antd `ConfigProvider`.
 * Mọi kích thước control được nâng lên mức thoải mái cho cảm ứng (tap target
 * ≥ 42px) và tự co lại trên màn hình nhỏ thông qua CSS của từng layout.
 *
 * @param {boolean} isDarkMode - true khi người dùng đang dùng dark mode
 * @returns {import('antd').ThemeConfig}
 */
export default function createAntdTheme(isDarkMode) {
  return {
    algorithm: isDarkMode ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
    token: {
      colorPrimary: isDarkMode ? BRAND_COLORS.primaryDark : BRAND_COLORS.primary,
      colorInfo: isDarkMode ? BRAND_COLORS.primaryDark : BRAND_COLORS.primary,
      colorLink: isDarkMode ? BRAND_COLORS.primaryDark : BRAND_COLORS.primary,
      colorLinkHover: isDarkMode ? BRAND_COLORS.primaryDarkHover : BRAND_COLORS.primaryHover,
      fontFamily: FONT_FAMILY,
      fontSize: 15,
      borderRadius: 10,
      borderRadiusLG: 14,
      controlHeight: 42,
      controlHeightLG: 48,
      controlHeightSM: 34,
      wireframe: false,
    },
    components: {
      Button: {
        fontWeight: 600,
        primaryShadow: 'none',
        defaultShadow: 'none',
        paddingInline: 20,
      },
      Card: {
        paddingLG: 28,
        headerFontSize: 16,
      },
      Form: {
        itemMarginBottom: 18,
        labelFontSize: 13,
        verticalLabelPadding: '0 0 6px',
      },
      Input: {
        paddingBlock: 10,
        paddingInline: 14,
        activeShadow: '0 0 0 3px rgba(124, 29, 255, 0.16)',
      },
      Alert: {
        paddingContentVertical: 12,
      },
      Typography: {
        titleMarginBottom: '0.4em',
        titleMarginTop: '0',
      },
    },
  }
}
