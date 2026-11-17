import { theme as antdTheme } from 'antd'
import { BRAND_COLORS, FONT_FAMILY } from './brandColors.js'

/**
 * Sinh cấu hình theme cho antd ConfigProvider với tone Xanh da trời & Vàng sáng.
 * Đảm bảo độ tương phản cao, chữ luôn đen sẫm rõ ràng (#0f172a), nền trắng tinh khôi,
 * hoàn toàn không bị tình trạng chữ trắng trên nền trắng hay ô nền đen lạc quẻ.
 */
export default function createAntdTheme() {
  return {
    algorithm: antdTheme.defaultAlgorithm,
    token: {
      colorPrimary: '#0284c7', // Sky Blue 600
      colorInfo: '#0ea5e9', // Sky Blue 500
      colorSuccess: '#10b981',
      colorWarning: '#f59e0b', // Vàng ấm Amber
      colorError: '#ef4444',
      colorText: '#0f172a', // Màu chữ đen sẫm sắc nét
      colorTextSecondary: '#475569',
      colorTextHeading: '#0f172a',
      colorBgContainer: '#ffffff', // Mọi ô nhập, card luôn nền trắng
      colorBgElevated: '#ffffff', // Dropdown, popover, modal luôn nền trắng
      colorBgLayout: '#f8fafc',
      colorBorder: '#bae6fd', // Viền xanh pastel nhẹ nhàng
      colorBorderSecondary: '#e2e8f0',
      colorLink: '#0284c7',
      colorLinkHover: '#0369a1',
      fontFamily: FONT_FAMILY,
      fontSize: 15,
      borderRadius: 10,
      borderRadiusLG: 14,
      controlHeight: 40,
      controlHeightLG: 46,
      controlHeightSM: 32,
      wireframe: false,
    },
    components: {
      Button: {
        fontWeight: 600,
        primaryShadow: '0 2px 8px rgba(2, 132, 199, 0.28)',
        defaultShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
        paddingInline: 18,
      },
      Card: {
        paddingLG: 24,
        headerFontSize: 16,
        colorBgContainer: '#ffffff',
      },
      Form: {
        itemMarginBottom: 18,
        labelFontSize: 13,
        verticalLabelPadding: '0 0 6px',
        labelColor: '#1e293b',
      },
      Input: {
        colorBgContainer: '#ffffff',
        colorText: '#0f172a',
        paddingBlock: 9,
        paddingInline: 14,
        activeShadow: '0 0 0 3px rgba(14, 165, 233, 0.18)',
        colorBorder: '#bae6fd',
      },
      Select: {
        colorBgContainer: '#ffffff',
        colorBgElevated: '#ffffff',
        colorText: '#0f172a',
        colorBorder: '#bae6fd',
        activeShadow: '0 0 0 3px rgba(14, 165, 233, 0.18)',
      },
      Table: {
        colorBgContainer: '#ffffff',
        headerBg: '#e0f2fe', // Nền header bảng xanh da trời nhạt êm dịu
        headerColor: '#0369a1', // Chữ header xanh đậm rõ ràng
        rowHoverBg: '#fefce8', // Hover dòng bảng đổi sang vàng nhạt ấm áp
        colorText: '#1e293b',
      },
      Menu: {
        colorBgContainer: '#ffffff',
        itemColor: '#334155',
        itemSelectedBg: '#e0f2fe',
        itemSelectedColor: '#0284c7',
        itemHoverBg: '#f0f9ff',
        itemHoverColor: '#0284c7',
      },
      Modal: {
        contentBg: '#ffffff',
        headerBg: '#ffffff',
      },
      Alert: {
        paddingContentVertical: 12,
      },
      Typography: {
        colorText: '#0f172a',
        colorTextHeading: '#0f172a',
        titleMarginBottom: '0.4em',
        titleMarginTop: '0',
      },
    },
  }
}
