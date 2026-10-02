import AppThemeProvider from './app/providers/AppThemeProvider.jsx'
import RootRouter from './app/router/RootRouter.jsx'

/**
 * Composition root cua Web Portal.
 * Chi lap provider (antd theme) va router — moi page/component nam trong src/app/**
 * theo cau truc module: app/components, app/layouts, app/features, app/hooks...
 */
export default function App() {
  return (
    <AppThemeProvider>
      <RootRouter />
    </AppThemeProvider>
  )
}