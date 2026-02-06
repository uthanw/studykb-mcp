import { reactive } from 'vue'

export interface Toast {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration: number
}

const state = reactive<{ toasts: Toast[] }>({
  toasts: [],
})

let nextId = 0

function addToast(type: Toast['type'], message: string, duration?: number) {
  const id = nextId++
  const defaultDuration = type === 'error' ? 5000 : 3000
  const toast: Toast = { id, type, message, duration: duration ?? defaultDuration }
  state.toasts.push(toast)

  setTimeout(() => {
    removeToast(id)
  }, toast.duration)

  return id
}

function removeToast(id: number) {
  const idx = state.toasts.findIndex(t => t.id === id)
  if (idx !== -1) {
    state.toasts.splice(idx, 1)
  }
}

export function useToast() {
  return {
    toasts: state.toasts,
    success: (msg: string, duration?: number) => addToast('success', msg, duration),
    error: (msg: string, duration?: number) => addToast('error', msg, duration),
    warning: (msg: string, duration?: number) => addToast('warning', msg, duration),
    info: (msg: string, duration?: number) => addToast('info', msg, duration),
    remove: removeToast,
  }
}
