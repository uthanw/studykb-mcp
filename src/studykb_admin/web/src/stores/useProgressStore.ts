import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchProgress,
  updateProgress,
  deleteProgress,
  type ProgressEntry,
  type ProgressStats,
} from '../api'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

export const statusOptions: { value: ProgressEntry['status']; label: string; color: string }[] = [
  { value: 'pending', label: '待学', color: 'slate' },
  { value: 'active', label: '进行中', color: 'sky' },
  { value: 'review', label: '复习', color: 'amber' },
  { value: 'done', label: '完成', color: 'green' },
]

export function getStatusColor(status: string) {
  switch (status) {
    case 'active': return 'text-sky-400 bg-sky-400/10'
    case 'review': return 'text-amber-400 bg-amber-400/10'
    case 'done': return 'text-green-400 bg-green-400/10'
    default: return 'text-slate-400 bg-slate-400/10'
  }
}

export function getStatusLabel(status: string) {
  const opt = statusOptions.find(o => o.value === status)
  return opt?.label || status
}

export const useProgressStore = defineStore('progress', () => {
  const toast = useToast()
  const { confirm } = useConfirm()

  // State
  const entries = ref<ProgressEntry[]>([])
  const stats = ref<ProgressStats | null>(null)
  const selectedEntry = ref<ProgressEntry | null>(null)
  const statusFilter = ref<string[]>([])
  const editMode = ref(false)
  const editData = ref<{ status: ProgressEntry['status'] | ''; comment: string }>({ status: '', comment: '' })
  const loading = ref(false)
  const error = ref<string | null>(null)

  // AbortController for request cancellation
  let currentAbortController: AbortController | null = null

  // Debounce timer for filter
  let filterDebounceTimer: ReturnType<typeof setTimeout> | null = null

  // Status sort order: active > review > pending > done
  const statusOrder: Record<string, number> = { active: 0, review: 1, pending: 2, done: 3 }

  // Computed
  const sortedEntries = computed(() => {
    return [...entries.value].sort((a, b) => {
      return (statusOrder[a.status] ?? 9) - (statusOrder[b.status] ?? 9)
    })
  })

  // Actions
  async function load(categoryName: string) {
    // Cancel previous request
    if (currentAbortController) {
      currentAbortController.abort()
    }
    currentAbortController = new AbortController()

    loading.value = true
    error.value = null
    try {
      const data = await fetchProgress(
        categoryName,
        statusFilter.value.length > 0 ? statusFilter.value : undefined
      )
      entries.value = data.entries
      stats.value = data.stats
    } catch (e: any) {
      if (e.name === 'AbortError') return
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  function selectEntry(entry: ProgressEntry) {
    selectedEntry.value = entry
    editMode.value = false
  }

  function startEdit() {
    if (!selectedEntry.value) return
    editData.value = {
      status: selectedEntry.value.status,
      comment: selectedEntry.value.comment,
    }
    editMode.value = true
  }

  async function saveEdit(categoryName: string) {
    if (!selectedEntry.value) return

    try {
      await updateProgress(categoryName, selectedEntry.value.id, {
        status: editData.value.status as ProgressEntry['status'],
        comment: editData.value.comment,
      })
      editMode.value = false
      await load(categoryName)
      selectedEntry.value = entries.value.find(e => e.id === selectedEntry.value?.id) || null
      toast.success('已保存')
    } catch (e: any) {
      toast.error(e.message || '保存失败')
    }
  }

  async function deleteEntry(categoryName: string) {
    if (!selectedEntry.value) return

    const ok = await confirm({
      title: '删除进度条目',
      message: `确定删除进度条目「${selectedEntry.value.name}」？`,
      type: 'danger',
      confirmText: '删除',
    })
    if (!ok) return

    try {
      await deleteProgress(categoryName, selectedEntry.value.id)
      selectedEntry.value = null
      await load(categoryName)
      toast.success('条目已删除')
    } catch (e: any) {
      toast.error(e.message || '删除失败')
    }
  }

  async function quickStatusChange(categoryName: string, entry: ProgressEntry, newStatus: ProgressEntry['status']) {
    // Optimistic update
    const oldStatus = entry.status
    entry.status = newStatus
    // Also update selectedEntry if it's the same
    if (selectedEntry.value?.id === entry.id) {
      selectedEntry.value = { ...selectedEntry.value, status: newStatus }
    }

    try {
      await updateProgress(categoryName, entry.id, {
        status: newStatus,
      })
      await load(categoryName)
      // Re-select if the same entry
      if (selectedEntry.value?.id === entry.id) {
        selectedEntry.value = entries.value.find(e => e.id === entry.id) || null
      }
    } catch (e: any) {
      // Rollback on failure
      entry.status = oldStatus
      if (selectedEntry.value?.id === entry.id) {
        selectedEntry.value = { ...selectedEntry.value, status: oldStatus }
      }
      toast.error(e.message || '状态更新失败')
    }
  }

  function toggleFilter(status: string, categoryName: string) {
    const index = statusFilter.value.indexOf(status)
    if (index >= 0) {
      statusFilter.value.splice(index, 1)
    } else {
      statusFilter.value.push(status)
    }

    // Debounce the load
    if (filterDebounceTimer) {
      clearTimeout(filterDebounceTimer)
    }
    filterDebounceTimer = setTimeout(() => {
      load(categoryName)
    }, 150)
  }

  function reset() {
    selectedEntry.value = null
    editMode.value = false
    entries.value = []
    stats.value = null
    if (currentAbortController) {
      currentAbortController.abort()
      currentAbortController = null
    }
    if (filterDebounceTimer) {
      clearTimeout(filterDebounceTimer)
      filterDebounceTimer = null
    }
  }

  return {
    // State
    entries,
    stats,
    selectedEntry,
    statusFilter,
    editMode,
    editData,
    loading,
    error,
    // Computed
    sortedEntries,
    // Actions
    load,
    selectEntry,
    startEdit,
    saveEdit,
    deleteEntry,
    quickStatusChange,
    toggleFilter,
    reset,
  }
})
