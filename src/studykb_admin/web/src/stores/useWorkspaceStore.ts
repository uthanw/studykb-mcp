import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listWorkspaceFiles,
  readWorkspaceFile,
  deleteWorkspaceFile,
  listFileHistory,
  getFileVersion,
  rollbackFile,
  type WorkspaceFile,
  type FileVersion,
} from '../api'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'
import { getFileIcon, isMarkdownFile } from '../utils/file'

export const useWorkspaceStore = defineStore('workspace', () => {
  const toast = useToast()
  const { confirm } = useConfirm()

  // ── Core state ────────────────────────────────────────
  const files = ref<WorkspaceFile[]>([])
  const selectedFile = ref<string | null>(null)
  const fileContent = ref<string>('')
  const loading = ref(false)

  // note.md content for info tab preview
  const noteContent = ref<string>('')
  const noteLoading = ref(false)

  // ── History state ─────────────────────────────────────
  const historyVersions = ref<FileVersion[]>([])
  const historyLoading = ref(false)
  const historyPanelOpen = ref(false)

  // ── Diff state ────────────────────────────────────────
  const diffMode = ref(false)
  const diffOldContent = ref('')
  const diffNewContent = ref('')
  const diffOldLabel = ref('')
  const diffNewLabel = ref('')
  const diffViewType = ref<'unified' | 'split'>('unified')

  // ── Note ──────────────────────────────────────────────

  async function loadNote(categoryName: string, progressId: string) {
    noteLoading.value = true
    try {
      const { content } = await readWorkspaceFile(categoryName, progressId, 'note.md')
      noteContent.value = content
    } catch {
      noteContent.value = ''
    } finally {
      noteLoading.value = false
    }
  }

  // ── Core actions ──────────────────────────────────────

  async function loadFiles(categoryName: string, progressId: string) {
    loading.value = true
    try {
      files.value = await listWorkspaceFiles(categoryName, progressId)
      const noteFile = files.value.find(f => f.path === 'note.md')
      if (noteFile && !selectedFile.value) {
        await selectFileAction(categoryName, progressId, 'note.md')
      }
    } catch (e: unknown) {
      files.value = []
      console.error('[Workspace] Failed to load files:', e)
    } finally {
      loading.value = false
    }
  }

  async function selectFileAction(categoryName: string, progressId: string, filePath: string) {
    selectedFile.value = filePath
    // Close diff when switching files
    closeDiff()
    loading.value = true
    try {
      const { content } = await readWorkspaceFile(categoryName, progressId, filePath)
      fileContent.value = content
    } catch (e: unknown) {
      fileContent.value = ''
      console.error('Failed to read workspace file:', e)
    } finally {
      loading.value = false
    }
    // Auto-load history if panel is open
    if (historyPanelOpen.value) {
      await loadHistory(categoryName, progressId, filePath)
    }
  }

  async function deleteFileAction(categoryName: string, progressId: string, filePath: string) {
    const ok = await confirm({
      title: '删除文件',
      message: `确定删除文件「${filePath}」？\n（文件内容会保存在历史记录中，可通过回滚恢复）`,
      type: 'danger',
      confirmText: '删除',
    })
    if (!ok) return

    try {
      await deleteWorkspaceFile(categoryName, progressId, filePath)
      if (selectedFile.value === filePath) {
        selectedFile.value = null
        fileContent.value = ''
        closeDiff()
      }
      await loadFiles(categoryName, progressId)
      toast.success(`文件「${filePath}」已删除`)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '删除文件失败'
      toast.error(msg)
    }
  }

  async function refresh(categoryName: string, progressId: string) {
    await loadFiles(categoryName, progressId)
    if (selectedFile.value) {
      await selectFileAction(categoryName, progressId, selectedFile.value)
    }
  }

  // ── History actions ───────────────────────────────────

  async function loadHistory(categoryName: string, progressId: string, filePath?: string) {
    const fp = filePath || selectedFile.value
    if (!fp) return

    historyLoading.value = true
    try {
      historyVersions.value = await listFileHistory(categoryName, progressId, fp)
    } catch (e: unknown) {
      historyVersions.value = []
      console.error('[Workspace] Failed to load history:', e)
    } finally {
      historyLoading.value = false
    }
  }

  async function viewVersion(
    categoryName: string,
    progressId: string,
    version: FileVersion
  ) {
    const fp = selectedFile.value
    if (!fp) return

    try {
      // 找到选中版本在列表中的位置（列表按时间倒序，idx+1 是上一版本）
      const idx = historyVersions.value.findIndex(v => v.version_id === version.version_id)
      const prevVersion = idx >= 0 && idx + 1 < historyVersions.value.length
        ? historyVersions.value[idx + 1]
        : null

      // 获取选中版本内容
      const newContent = await getFileVersion(categoryName, progressId, fp, version.version_id)

      // 获取上一版本内容（没有则为空，表示从无到有）
      const oldContent = prevVersion
        ? await getFileVersion(categoryName, progressId, fp, prevVersion.version_id)
        : ''

      diffMode.value = true
      diffOldContent.value = oldContent
      diffNewContent.value = newContent
      diffOldLabel.value = prevVersion
        ? `${prevVersion.description} (${formatTime(prevVersion.timestamp)})`
        : '（无）'
      diffNewLabel.value = `${version.description} (${formatTime(version.timestamp)})`
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '获取版本内容失败'
      toast.error(msg)
    }
  }

  async function rollbackToVersion(
    categoryName: string,
    progressId: string,
    version: FileVersion
  ) {
    const fp = selectedFile.value
    if (!fp) return

    const ok = await confirm({
      title: '回滚文件',
      message: `确定将「${fp}」回滚到 ${formatTime(version.timestamp)} 的版本？\n当前内容会自动保存为一个新的历史快照。`,
      type: 'warning',
      confirmText: '回滚',
    })
    if (!ok) return

    try {
      await rollbackFile(categoryName, progressId, fp, version.version_id)
      closeDiff()
      // Refresh file content and history
      await selectFileAction(categoryName, progressId, fp)
      await loadHistory(categoryName, progressId, fp)
      toast.success('文件已回滚')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '回滚失败'
      toast.error(msg)
    }
  }

  function closeDiff() {
    diffMode.value = false
    diffOldContent.value = ''
    diffNewContent.value = ''
    diffOldLabel.value = ''
    diffNewLabel.value = ''
  }

  function toggleHistoryPanel() {
    historyPanelOpen.value = !historyPanelOpen.value
  }

  // ── Reset ─────────────────────────────────────────────

  function reset() {
    files.value = []
    selectedFile.value = null
    fileContent.value = ''
    loading.value = false
    noteContent.value = ''
    noteLoading.value = false
    // Reset history
    historyVersions.value = []
    historyLoading.value = false
    historyPanelOpen.value = false
    closeDiff()
  }

  return {
    // Core state
    files,
    selectedFile,
    fileContent,
    loading,
    noteContent,
    noteLoading,
    // History state
    historyVersions,
    historyLoading,
    historyPanelOpen,
    // Diff state
    diffMode,
    diffOldContent,
    diffNewContent,
    diffOldLabel,
    diffNewLabel,
    diffViewType,
    // Core actions
    loadNote,
    loadFiles,
    selectFile: selectFileAction,
    deleteFile: deleteFileAction,
    refresh,
    // History actions
    loadHistory,
    viewVersion,
    rollbackToVersion,
    closeDiff,
    toggleHistoryPanel,
    // Reset
    reset,
    // Helpers (re-exported from utils)
    getFileIcon,
    isMarkdownFile,
  }
})

// ── Helpers ─────────────────────────────────────────────────

function formatTime(ts: string): string {
  try {
    const d = new Date(ts)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return ts
  }
}
