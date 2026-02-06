import { watch } from 'vue'
import { useRoute } from 'vue-router'
import { useCategoryStore } from '../stores/useCategoryStore'
import { useProgressStore } from '../stores/useProgressStore'
import { useWorkspaceStore } from '../stores/useWorkspaceStore'

/**
 * Encapsulates cross-store coordination logic driven by route changes:
 * - Category change → reset progress + workspace + load progress
 * - Entry selection → reset workspace + load note
 */
export function useCategoryWorkflow() {
  const route = useRoute()
  const categoryStore = useCategoryStore()
  const progressStore = useProgressStore()
  const workspace = useWorkspaceStore()

  // Sync route params → store
  watch(
    () => route.params.name as string | undefined,
    (name) => {
      if (name && name !== categoryStore.selectedCategoryName) {
        categoryStore.selectCategory(name)
      }
    },
    { immediate: true }
  )

  // Category change → reset progress + workspace + reload
  watch(
    () => categoryStore.selectedCategoryName,
    (name) => {
      progressStore.reset()
      workspace.reset()
      const tab = route.query.tab as string
      if (tab === 'progress' && name) {
        progressStore.load(name)
      }
    }
  )

  // Entry selection → reset workspace & load note
  watch(
    () => progressStore.selectedEntry,
    (newEntry) => {
      if (newEntry) {
        workspace.reset()
        if (categoryStore.selectedCategoryName) {
          workspace.loadNote(categoryStore.selectedCategoryName, newEntry.id)
        }
      }
    }
  )
}
