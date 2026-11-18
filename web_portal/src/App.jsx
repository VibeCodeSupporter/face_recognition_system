import AppThemeProvider from './app/providers/AppThemeProvider.jsx'
import AuthProvider from './app/providers/AuthProvider.jsx'
import RootRouter from './app/router/RootRouter.jsx'

/**
 * Composition root của Web Portal FaceAccess.
 * Lắp provider Ant Design theme, AuthProvider và router điều hướng.
 */
export default function App() {
  return (
    <AppThemeProvider>
      <AuthProvider>
        <RootRouter />
      </AuthProvider>
    </AppThemeProvider>
  )
}
