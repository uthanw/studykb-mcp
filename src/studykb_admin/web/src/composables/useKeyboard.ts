import { onKeyStroke } from '@vueuse/core'
import { useRoute } from 'vue-router'
import { useProgressStore } from '../stores/useProgressStore'

/**
 * Global keyboard shortcuts:
 * - Escape: go back one level (close detail → deselect entry → close modal)
 * - ↑↓: navigate progress entry list
 * - Ctrl+N / Cmd+N: new category
 */
export function useKeyboard(options: {
  onNewCategory?: () => void
} = {}) {
  const route = useRoute()
  const progressStore = useProgressStore()

  // Escape: go back one level
  onKeyStroke('Escape', (e) => {
    // Don't intercept if a modal/dialog is open (handled by the modal itself)
    // or if focused in an input/textarea
    const el = document.activeElement
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement) {
      return
    }

    e.preventDefault()

    if (progressStore.selectedEntry) {
      progressStore.selectedEntry = null
    }
  })

  // Arrow up/down: navigate progress entries
  onKeyStroke('ArrowDown', (e) => {
    const el = document.activeElement
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return

    if (route.query.tab === 'progress' && !progressStore.selectedEntry) {
      e.preventDefault()
      const entries = progressStore.sortedEntries
      if (entries.length === 0) return

      // Find current or select first
      const currentIndex = entries.findIndex(e => e.id === progressStore.selectedEntry?.id)
      const nextIndex = currentIndex < 0 ? 0 : Math.min(currentIndex + 1, entries.length - 1)
      progressStore.selectEntry(entries[nextIndex])
    }
  })

  onKeyStroke('ArrowUp', (e) => {
    const el = document.activeElement
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return

    if (route.query.tab === 'progress' && !progressStore.selectedEntry) {
      e.preventDefault()
      const entries = progressStore.sortedEntries
      if (entries.length === 0) return

      const currentIndex = entries.findIndex(e => e.id === progressStore.selectedEntry?.id)
      const prevIndex = currentIndex <= 0 ? 0 : currentIndex - 1
      progressStore.selectEntry(entries[prevIndex])
    }
  })

  // Ctrl+N / Cmd+N: new category
  onKeyStroke('n', (e) => {
    if (e.metaKey || e.ctrlKey) {
      e.preventDefault()
      options.onNewCategory?.()
    }
  })
}
