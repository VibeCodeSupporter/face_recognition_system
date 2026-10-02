import { useCallback, useEffect, useState } from 'react'

/** Đọc path hiện tại từ hash (bỏ qua query phía sau). */
function readPathFromHash() {
  const rawHash = window.location.hash.replace(/^#/, '')
  const [path] = rawHash.split('?')
  return path || ''
}

/**
 * Hook điều hướng tối giản dựa trên hash của URL.
 * Không cần thêm dependency router; API đủ dùng cho giai đoạn UI:
 * `#/login`, `#/register`, `#/forgot-password`, `#/dashboard`.
 *
 * @returns {{ path: string, navigate: (nextPath: string, options?: { replace?: boolean }) => void }}
 */
export default function useHashRoute() {
  const [path, setPath] = useState(readPathFromHash)

  useEffect(() => {
    const handleHashChange = () => setPath(readPathFromHash())
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const navigate = useCallback((nextPath, { replace = false } = {}) => {
    const targetHash = `#${nextPath}`

    if (window.location.hash === targetHash) {
      return
    }

    if (replace) {
      window.history.replaceState(null, '', targetHash)
      setPath(readPathFromHash())
      return
    }

    window.location.hash = nextPath
  }, [])

  return { path, navigate }
}
