<script setup lang="ts">
import { useConfirm } from '../../composables/useConfirm'

const { state, handleConfirm, handleCancel } = useConfirm()

const typeStyles = {
  danger: {
    confirmBtn: 'bg-red-600 hover:bg-red-500 text-white',
    icon: 'text-red-400 bg-red-500/10',
  },
  warning: {
    confirmBtn: 'bg-amber-600 hover:bg-amber-500 text-white',
    icon: 'text-amber-400 bg-amber-500/10',
  },
  info: {
    confirmBtn: 'bg-sky-600 hover:bg-sky-500 text-white',
    icon: 'text-sky-400 bg-sky-500/10',
  },
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    handleConfirm()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    handleCancel()
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="confirm-dialog">
      <div
        v-if="state.visible"
        class="fixed inset-0 z-[9500] flex items-center justify-center"
        @keydown="onKeydown"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/60 backdrop-blur-sm"
          @click="handleCancel"
        />

        <!-- Dialog -->
        <div
          class="relative bg-slate-800 rounded-xl shadow-2xl border border-slate-700/50 w-[420px] max-w-[90vw] overflow-hidden"
          tabindex="-1"
        >
          <div class="p-6">
            <!-- Icon + Title -->
            <div class="flex items-start gap-4">
              <div
                class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                :class="typeStyles[state.options.type || 'info'].icon"
              >
                <!-- Danger icon -->
                <svg v-if="state.options.type === 'danger'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                <!-- Warning icon -->
                <svg v-else-if="state.options.type === 'warning'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <!-- Info icon -->
                <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>

              <div class="flex-1 min-w-0">
                <h3 class="text-lg font-semibold text-slate-100">{{ state.options.title }}</h3>
                <p class="mt-2 text-sm text-slate-400 leading-relaxed">{{ state.options.message }}</p>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="px-6 py-4 bg-slate-800/50 border-t border-slate-700/50 flex justify-end gap-3">
            <button
              class="px-4 py-2 text-sm text-slate-300 hover:text-slate-100 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
              @click="handleCancel"
            >
              {{ state.options.cancelText }}
            </button>
            <button
              class="px-4 py-2 text-sm rounded-lg transition-colors"
              :class="typeStyles[state.options.type || 'info'].confirmBtn"
              @click="handleConfirm"
            >
              {{ state.options.confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.confirm-dialog-enter-active,
.confirm-dialog-leave-active {
  transition: opacity 0.1s ease;
}
.confirm-dialog-enter-from,
.confirm-dialog-leave-to {
  opacity: 0;
}
</style>
