import { reactive } from 'vue'

export interface ConfirmOptions {
  title: string
  message: string
  type?: 'danger' | 'warning' | 'info'
  confirmText?: string
  cancelText?: string
}

interface ConfirmState {
  visible: boolean
  options: ConfirmOptions
  resolve: ((value: boolean) => void) | null
}

const state = reactive<ConfirmState>({
  visible: false,
  options: {
    title: '',
    message: '',
    type: 'info',
    confirmText: '确认',
    cancelText: '取消',
  },
  resolve: null,
})

export function useConfirm() {
  function confirm(options: ConfirmOptions): Promise<boolean> {
    state.options = {
      confirmText: '确认',
      cancelText: '取消',
      type: 'info',
      ...options,
    }
    state.visible = true

    return new Promise<boolean>((resolve) => {
      state.resolve = resolve
    })
  }

  function handleConfirm() {
    state.visible = false
    state.resolve?.(true)
    state.resolve = null
  }

  function handleCancel() {
    state.visible = false
    state.resolve?.(false)
    state.resolve = null
  }

  return {
    state,
    confirm,
    handleConfirm,
    handleCancel,
  }
}
