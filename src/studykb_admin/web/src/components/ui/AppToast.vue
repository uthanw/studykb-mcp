<script setup lang="ts">
import { useToast, type Toast } from '../../composables/useToast'

const { toasts, remove } = useToast()

const typeConfig: Record<Toast['type'], { color: string; icon: string }> = {
  success: { color: 'bg-green-500', icon: '✓' },
  error: { color: 'bg-red-500', icon: '✕' },
  warning: { color: 'bg-amber-500', icon: '!' },
  info: { color: 'bg-sky-500', icon: 'i' },
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-[9999] flex flex-col gap-3 pointer-events-none">
      <TransitionGroup
        name="toast"
        tag="div"
        class="flex flex-col gap-3"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-stretch rounded-lg shadow-xl overflow-hidden backdrop-blur-sm bg-slate-800/95 border border-slate-700/50 min-w-[320px] max-w-[420px]"
        >
          <!-- Color strip -->
          <div
            class="w-1 flex-shrink-0"
            :class="typeConfig[toast.type].color"
          />

          <!-- Content -->
          <div class="flex items-center gap-3 px-4 py-3 flex-1 min-w-0">
            <!-- Icon -->
            <div
              class="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold text-white"
              :class="typeConfig[toast.type].color"
            >
              {{ typeConfig[toast.type].icon }}
            </div>

            <!-- Message -->
            <p class="text-sm text-slate-200 flex-1 min-w-0 break-words">
              {{ toast.message }}
            </p>

            <!-- Close button -->
            <button
              class="flex-shrink-0 p-1 text-slate-400 hover:text-slate-200 transition-colors"
              @click="remove(toast.id)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.12s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
}
.toast-move {
  transition: transform 0.12s ease;
}
</style>
