import { createContext, ReactNode, useCallback, useContext, useMemo, useState } from 'react'

type ToastKind = 'success' | 'error' | 'info'

type ToastItem = {
  id: number
  kind: ToastKind
  message: string
}

type ToastContextValue = {
  pushToast: (message: string, kind?: ToastKind) => void
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)

const toneClass: Record<ToastKind, string> = {
  success: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
  error: 'border-rose-500/45 bg-rose-500/10 text-rose-200',
  info: 'border-neonOrange/50 bg-neonOrange/12 text-neonOrange',
}

export const ToastProvider = ({ children }: { children: ReactNode }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const pushToast = useCallback((message: string, kind: ToastKind = 'info') => {
    const id = Date.now() + Math.floor(Math.random() * 1000)
    setToasts((current) => [...current, { id, kind, message }])
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id))
    }, 3600)
  }, [])

  const value = useMemo(() => ({ pushToast }), [pushToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-[120] flex w-[min(92vw,420px)] flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto rounded-xl border px-3 py-2 text-sm shadow-neon backdrop-blur ${toneClass[toast.kind]}`}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}
