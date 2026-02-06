<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'

const props = withDefaults(defineProps<{
  visible: boolean
  title?: string
  width?: string
}>(), {
  title: '',
  width: '480px',
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const show = computed({
  get: () => props.visible,
  set: (val: boolean) => emit('update:visible', val),
})

const panelRef = ref<HTMLElement | null>(null)

function close() {
  show.value = false
}

function onBackdropClick() {
  close()
}

// Focus trap: on open, focus the panel
watch(() => props.visible, async (val) => {
  if (val) {
    await nextTick()
    // Focus the first focusable element inside the panel
    if (panelRef.value) {
      const focusable = panelRef.value.querySelector<HTMLElement>(
        'input, button, textarea, select, [tabindex]:not([tabindex="-1"])'
      )
      focusable?.focus()
    }
  }
})

// Tab trap: keep focus within modal
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    close()
    return
  }

  if (e.key === 'Tab' && panelRef.value) {
    const focusableEls = panelRef.value.querySelectorAll<HTMLElement>(
      'input:not([disabled]), button:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
    if (focusableEls.length === 0) return

    const first = focusableEls[0]
    const last = focusableEls[focusableEls.length - 1]

    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault()
        last.focus()
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="show"
        class="fixed inset-0 z-[9000] flex items-center justify-center"
        @keydown="onKeydown"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/60 backdrop-blur-sm"
          @click="onBackdropClick"
        />

        <!-- Panel -->
        <div
          ref="panelRef"
          class="relative bg-slate-800 rounded-xl shadow-2xl border border-slate-700/50 overflow-hidden"
          :style="{ width, maxWidth: '90vw', maxHeight: '90vh' }"
          tabindex="-1"
        >
          <!-- Header -->
          <div v-if="title" class="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
            <h3 class="text-lg font-semibold text-slate-100">{{ title }}</h3>
            <button
              class="p-1 text-slate-400 hover:text-slate-200 transition-colors rounded-lg hover:bg-slate-700/50"
              @click="close"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Content -->
          <div class="overflow-y-auto" style="max-height: calc(90vh - 80px)">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.1s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
