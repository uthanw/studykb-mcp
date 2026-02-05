<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  fetchCategories,
  createCategory,
  deleteCategory,
  deleteMaterial,
  uploadMaterial,
  generateIndex,
  initProgress,
  fetchProgress,
  updateProgress,
  deleteProgress,
  listWorkspaceFiles,
  readWorkspaceFile,
  deleteWorkspaceFile,
  type Category,
  type ProgressEntry,
  type ProgressStats,
  type WorkspaceFile,
} from '../api'
import McpConfigBox from '../components/McpConfigBox.vue'
import TaskProgressPanel from '../components/TaskProgressPanel.vue'
import MarkdownViewer from '../components/MarkdownViewer.vue'

// State - Common
const categories = ref<Category[]>([])
const selectedCategory = ref<string | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const showNewCategoryModal = ref(false)
const newCategoryName = ref('')
const taskPanel = ref<InstanceType<typeof TaskProgressPanel> | null>(null)
const mcpCollapsed = ref(true)
const taskPanelCollapsed = ref(true)

// State - Tab
const activeTab = ref<'materials' | 'progress'>('materials')

// State - Materials
const selectedMaterials = ref<Set<string>>(new Set())
const uploading = ref(false)
const uploadProgress = ref<string | null>(null)

// State - Progress
const entries = ref<ProgressEntry[]>([])
const stats = ref<ProgressStats | null>(null)
const selectedEntry = ref<ProgressEntry | null>(null)
const statusFilter = ref<string[]>([])
const editMode = ref(false)
const editData = ref({
  status: '',
  comment: '',
})
const progressLoading = ref(false)

// State - Workspace
const detailTab = ref<'info' | 'workspace'>('info')
const workspaceFiles = ref<WorkspaceFile[]>([])
const selectedWorkspaceFile = ref<string | null>(null)
const workspaceFileContent = ref<string>('')
const workspaceLoading = ref(false)

const statusOptions = [
  { value: 'pending', label: '待学', color: 'slate' },
  { value: 'active', label: '进行中', color: 'sky' },
  { value: 'review', label: '复习', color: 'amber' },
  { value: 'done', label: '完成', color: 'green' },
]

// Computed
const currentCategory = computed(() => {
  return categories.value.find(c => c.name === selectedCategory.value) || null
})

const materials = computed(() => {
  return currentCategory.value?.materials || []
})

const hasSelectedMaterials = computed(() => selectedMaterials.value.size > 0)

// Methods
async function loadCategories() {
  loading.value = true
  error.value = null
  try {
    categories.value = await fetchCategories()
    // Auto-select first category if none selected
    if (!selectedCategory.value && categories.value.length > 0) {
      selectedCategory.value = categories.value[0].name
    }
  } catch (e: any) {
    error.value = e.message || '加载分类失败'
  } finally {
    loading.value = false
  }
}

function selectCategory(name: string) {
  selectedCategory.value = name
  selectedMaterials.value.clear()
  // Reset progress state when switching category
  selectedEntry.value = null
  editMode.value = false
  // If on progress tab, reload progress
  if (activeTab.value === 'progress') {
    loadProgress()
  }
}

function toggleMaterial(name: string) {
  if (selectedMaterials.value.has(name)) {
    selectedMaterials.value.delete(name)
  } else {
    selectedMaterials.value.add(name)
  }
  // Trigger reactivity
  selectedMaterials.value = new Set(selectedMaterials.value)
}

function selectAllMaterials() {
  if (selectedMaterials.value.size === materials.value.length) {
    selectedMaterials.value.clear()
  } else {
    selectedMaterials.value = new Set(materials.value.map(m => m.name))
  }
}

async function handleCreateCategory() {
  if (!newCategoryName.value.trim()) return

  try {
    await createCategory(newCategoryName.value.trim())
    await loadCategories()
    selectedCategory.value = newCategoryName.value.trim()
    newCategoryName.value = ''
    showNewCategoryModal.value = false
  } catch (e: any) {
    alert(e.message || '创建分类失败')
  }
}

async function handleDeleteCategory(name: string) {
  if (!confirm(`确定要删除分类「${name}」及其所有内容吗？`)) return

  try {
    await deleteCategory(name)
    if (selectedCategory.value === name) {
      selectedCategory.value = null
    }
    await loadCategories()
  } catch (e: any) {
    alert(e.message || '删除分类失败')
  }
}

async function handleDeleteMaterial(material: string) {
  if (!selectedCategory.value) return
  if (!confirm(`确定要删除资料「${material}」吗？`)) return

  try {
    await deleteMaterial(selectedCategory.value, material)
    selectedMaterials.value.delete(material)
    await loadCategories()
  } catch (e: any) {
    alert(e.message || '删除资料失败')
  }
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (!files || files.length === 0 || !selectedCategory.value) return

  uploading.value = true
  uploadProgress.value = null

  // Get session ID and connect WebSocket before upload
  const sessionId = taskPanel.value?.getSessionId() || ''
  taskPanel.value?.connect()

  try {
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      uploadProgress.value = `上传中 (${i + 1}/${files.length}): ${file.name}`

      // Pass sessionId for WebSocket progress updates
      const result = await uploadMaterial(selectedCategory.value, file, false, sessionId)

      if (result.type === 'conversion') {
        uploadProgress.value = `已启动转换: ${file.name}`
        // Start task tracking in panel
        taskPanel.value?.startTask(`转换 ${file.name}`)
      }
    }

    await loadCategories()
    uploadProgress.value = '上传完成'
    setTimeout(() => { uploadProgress.value = null }, 2000)
  } catch (e: any) {
    uploadProgress.value = `上传失败: ${e.message}`
  } finally {
    uploading.value = false
    target.value = ''
  }
}

async function handleGenerateIndex() {
  if (!selectedCategory.value || selectedMaterials.value.size === 0) return

  const sessionId = taskPanel.value?.getSessionId() || ''
  taskPanel.value?.startTask('生成索引')
  taskPanel.value?.connect()

  try {
    for (const material of selectedMaterials.value) {
      await generateIndex(selectedCategory.value, material, sessionId)
    }
  } catch (e: any) {
    alert(e.message || '启动索引生成失败')
  }
}

async function handleInitProgress() {
  if (!selectedCategory.value) return

  const sessionId = taskPanel.value?.getSessionId() || ''
  taskPanel.value?.startTask('初始化进度')
  taskPanel.value?.connect()

  try {
    await initProgress(selectedCategory.value, sessionId)
  } catch (e: any) {
    alert(e.message || '启动进度初始化失败')
  }
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  const files = event.dataTransfer?.files
  if (!files || files.length === 0 || !selectedCategory.value) return

  // Create a fake input event
  const fakeEvent = {
    target: { files, value: '' }
  } as unknown as Event
  handleFileUpload(fakeEvent)
}

function handleDragOver(event: DragEvent) {
  event.preventDefault()
}

onMounted(() => {
  loadCategories()
})

// Reload when task completes
function handleTaskComplete() {
  loadCategories()
  if (activeTab.value === 'progress') {
    loadProgress()
  }
}

// Progress Management Methods
async function loadProgress() {
  if (!selectedCategory.value) return

  progressLoading.value = true
  error.value = null
  try {
    const data = await fetchProgress(selectedCategory.value, statusFilter.value.length > 0 ? statusFilter.value : undefined)
    entries.value = data.entries
    stats.value = data.stats
  } catch (e: any) {
    error.value = e.message
  } finally {
    progressLoading.value = false
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

async function saveEdit() {
  if (!selectedEntry.value || !selectedCategory.value) return

  try {
    await updateProgress(selectedCategory.value, selectedEntry.value.id, {
      status: editData.value.status as any,
      comment: editData.value.comment,
    })
    editMode.value = false
    await loadProgress()
    // Re-select the updated entry
    selectedEntry.value = entries.value.find(e => e.id === selectedEntry.value?.id) || null
  } catch (e: any) {
    error.value = e.message
  }
}

async function handleDeleteEntry() {
  if (!selectedEntry.value || !selectedCategory.value) return
  if (!confirm(`确定删除进度条目 "${selectedEntry.value.name}"？`)) return

  try {
    await deleteProgress(selectedCategory.value, selectedEntry.value.id)
    selectedEntry.value = null
    await loadProgress()
  } catch (e: any) {
    error.value = e.message
  }
}

async function quickStatusChange(entry: ProgressEntry, newStatus: string) {
  if (!selectedCategory.value) return

  try {
    await updateProgress(selectedCategory.value, entry.id, {
      status: newStatus as any,
    })
    await loadProgress()
  } catch (e: any) {
    error.value = e.message
  }
}

function toggleFilter(status: string) {
  const index = statusFilter.value.indexOf(status)
  if (index >= 0) {
    statusFilter.value.splice(index, 1)
  } else {
    statusFilter.value.push(status)
  }
  loadProgress()
}

function getStatusColor(status: string) {
  switch (status) {
    case 'active': return 'text-sky-400 bg-sky-400/10'
    case 'review': return 'text-amber-400 bg-amber-400/10'
    case 'done': return 'text-green-400 bg-green-400/10'
    default: return 'text-slate-400 bg-slate-400/10'
  }
}

function getStatusLabel(status: string) {
  const opt = statusOptions.find(o => o.value === status)
  return opt?.label || status
}

function handleTabChange(tab: 'materials' | 'progress') {
  activeTab.value = tab
  if (tab === 'progress' && selectedCategory.value) {
    loadProgress()
  }
}

// Workspace Methods
async function loadWorkspaceFiles() {
  if (!selectedCategory.value || !selectedEntry.value) return

  workspaceLoading.value = true
  try {
    workspaceFiles.value = await listWorkspaceFiles(selectedCategory.value, selectedEntry.value.id)
    // Auto-select note.md if exists
    const noteFile = workspaceFiles.value.find(f => f.path === 'note.md')
    if (noteFile && !selectedWorkspaceFile.value) {
      await selectWorkspaceFile('note.md')
    }
  } catch (e: any) {
    workspaceFiles.value = []
    console.error('Failed to load workspace files:', e)
  } finally {
    workspaceLoading.value = false
  }
}

async function selectWorkspaceFile(filePath: string) {
  if (!selectedCategory.value || !selectedEntry.value) return

  selectedWorkspaceFile.value = filePath
  workspaceLoading.value = true
  try {
    const { content } = await readWorkspaceFile(selectedCategory.value, selectedEntry.value.id, filePath)
    workspaceFileContent.value = content
  } catch (e: any) {
    workspaceFileContent.value = ''
    console.error('Failed to read workspace file:', e)
  } finally {
    workspaceLoading.value = false
  }
}

async function handleDeleteWorkspaceFile(filePath: string) {
  if (!selectedCategory.value || !selectedEntry.value) return
  if (!confirm(`确定删除文件 "${filePath}"？`)) return

  try {
    await deleteWorkspaceFile(selectedCategory.value, selectedEntry.value.id, filePath)
    if (selectedWorkspaceFile.value === filePath) {
      selectedWorkspaceFile.value = null
      workspaceFileContent.value = ''
    }
    await loadWorkspaceFiles()
  } catch (e: any) {
    alert(e.message || '删除文件失败')
  }
}

function handleDetailTabChange(tab: 'info' | 'workspace') {
  detailTab.value = tab
  if (tab === 'workspace') {
    loadWorkspaceFiles()
  }
}

function getFileIcon(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase()
  switch (ext) {
    case 'md': return '📝'
    case 'py': return '🐍'
    case 'js':
    case 'ts': return '📜'
    case 'json': return '📋'
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif': return '🖼️'
    default: return '📄'
  }
}

function isMarkdownFile(path: string): boolean {
  return path.endsWith('.md')
}

// Watch for entry selection change - reset workspace state
watch(selectedEntry, (newEntry) => {
  if (newEntry) {
    detailTab.value = 'info'
    selectedWorkspaceFile.value = null
    workspaceFileContent.value = ''
    workspaceFiles.value = []
  }
})
</script>

<template>
  <div class="category-manager h-full flex flex-col">
    <!-- MCP Config Box -->
    <div class="flex-shrink-0 p-4 border-b border-slate-700">
      <McpConfigBox v-model:collapsed="mcpCollapsed" />
    </div>

    <!-- Main Content -->
    <div class="flex-1 flex min-h-0">
      <!-- Sidebar: Category List -->
      <div class="w-64 flex-shrink-0 border-r border-slate-700 flex flex-col">
        <div class="p-3 border-b border-slate-700 flex items-center justify-between">
          <span class="text-sm font-medium text-slate-300">分类列表</span>
          <button
            class="text-xs px-2 py-1 bg-sky-500/20 text-sky-400 rounded hover:bg-sky-500/30 transition-colors"
            @click="showNewCategoryModal = true"
          >
            + 新建
          </button>
        </div>

        <div class="flex-1 overflow-y-auto">
          <div v-if="loading" class="p-4 text-center text-slate-500">
            加载中...
          </div>
          <div v-else-if="error" class="p-4 text-center text-red-400">
            {{ error }}
          </div>
          <div v-else-if="categories.length === 0" class="p-4 text-center text-slate-500">
            暂无分类
          </div>
          <div v-else class="py-2">
            <div
              v-for="cat in categories"
              :key="cat.name"
              class="group px-3 py-2 cursor-pointer transition-colors flex items-center justify-between"
              :class="selectedCategory === cat.name ? 'bg-sky-500/20 text-sky-400' : 'text-slate-300 hover:bg-slate-800'"
              @click="selectCategory(cat.name)"
            >
              <div class="flex items-center gap-2 min-w-0">
                <span class="text-lg">📁</span>
                <span class="truncate">{{ cat.name }}</span>
                <span class="text-xs text-slate-500">({{ cat.file_count }})</span>
              </div>
              <button
                class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-1"
                title="删除分类"
                @click.stop="handleDeleteCategory(cat.name)"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Panel -->
      <div class="flex-1 flex flex-col min-w-0">
        <!-- Tab Header -->
        <div class="flex-shrink-0 border-b border-slate-700">
          <div class="flex">
            <button
              class="px-6 py-3 text-sm font-medium transition-colors relative"
              :class="activeTab === 'materials' ? 'text-sky-400' : 'text-slate-400 hover:text-slate-300'"
              @click="handleTabChange('materials')"
            >
              资料管理
              <span
                v-if="activeTab === 'materials'"
                class="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-400"
              ></span>
            </button>
            <button
              class="px-6 py-3 text-sm font-medium transition-colors relative"
              :class="activeTab === 'progress' ? 'text-sky-400' : 'text-slate-400 hover:text-slate-300'"
              @click="handleTabChange('progress')"
            >
              进度管理
              <span
                v-if="activeTab === 'progress'"
                class="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-400"
              ></span>
            </button>
          </div>
        </div>

        <!-- Materials Tab Content -->
        <template v-if="activeTab === 'materials'">
          <!-- Toolbar -->
          <div class="flex-shrink-0 p-3 border-b border-slate-700 flex items-center gap-3 flex-wrap">
            <label
              class="px-3 py-1.5 text-sm bg-sky-500/20 text-sky-400 rounded cursor-pointer hover:bg-sky-500/30 transition-colors flex items-center gap-1.5"
              :class="{ 'opacity-50 cursor-not-allowed': !selectedCategory || uploading }"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              上传资料
              <input
                type="file"
                class="hidden"
                multiple
                accept=".md,.pdf,.doc,.docx,.ppt,.pptx"
                :disabled="!selectedCategory || uploading"
                @change="handleFileUpload"
              />
            </label>

            <button
              class="px-3 py-1.5 text-sm bg-amber-500/20 text-amber-400 rounded hover:bg-amber-500/30 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!hasSelectedMaterials"
              @click="handleGenerateIndex"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
              </svg>
              生成索引
            </button>

            <button
              class="px-3 py-1.5 text-sm bg-green-500/20 text-green-400 rounded hover:bg-green-500/30 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!selectedCategory"
              @click="handleInitProgress"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              初始化进度
            </button>

            <div v-if="uploadProgress" class="text-sm text-slate-400">
              {{ uploadProgress }}
            </div>

            <div class="flex-1"></div>

            <button
              v-if="materials.length > 0"
              class="text-xs text-slate-400 hover:text-slate-300"
              @click="selectAllMaterials"
            >
              {{ selectedMaterials.size === materials.length ? '取消全选' : '全选' }}
            </button>
          </div>

          <!-- Materials Grid -->
          <div
            class="flex-1 overflow-y-auto p-4"
            @drop="handleDrop"
            @dragover="handleDragOver"
          >
            <div v-if="!selectedCategory" class="h-full flex items-center justify-center text-slate-500">
              请选择一个分类
            </div>
            <div v-else-if="materials.length === 0" class="h-full flex flex-col items-center justify-center text-slate-500 gap-4">
              <div class="text-lg">暂无资料</div>
              <div class="text-sm">拖拽文件到此处上传，或点击上方「上传资料」按钮</div>
              <div class="text-xs text-slate-600">支持格式: .md, .pdf, .doc, .docx, .ppt, .pptx</div>
            </div>
            <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              <div
                v-for="mat in materials"
                :key="mat.name"
                class="bg-slate-800 rounded-lg p-4 border-2 transition-all cursor-pointer group"
                :class="selectedMaterials.has(mat.name) ? 'border-sky-500' : 'border-transparent hover:border-slate-600'"
                @click="toggleMaterial(mat.name)"
              >
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0 flex-1">
                    <div class="font-medium text-slate-200 truncate" :title="mat.name">
                      {{ mat.name.replace('.md', '') }}
                    </div>
                    <div class="text-xs text-slate-500 mt-1">
                      {{ mat.line_count.toLocaleString() }} 行
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <span
                      v-if="mat.has_index"
                      class="text-xs px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded"
                    >
                      索引
                    </span>
                    <button
                      class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-1"
                      title="删除资料"
                      @click.stop="handleDeleteMaterial(mat.name)"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Progress Tab Content -->
        <template v-else>
          <!-- Progress Header with Stats -->
          <div class="flex-shrink-0 px-4 py-3 border-b border-slate-700">
            <div class="flex items-center justify-between">
              <div v-if="stats" class="text-sm text-slate-400">
                待学 <span class="text-slate-200">{{ stats.pending }}</span> ·
                进行中 <span class="text-sky-400">{{ stats.active }}</span> ·
                复习 <span class="text-amber-400">{{ stats.review }}</span> ·
                完成 <span class="text-green-400">{{ stats.done }}</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-sm text-slate-500">筛选:</span>
                <button
                  v-for="opt in statusOptions"
                  :key="opt.value"
                  class="px-2 py-1 rounded text-xs transition-colors"
                  :class="statusFilter.includes(opt.value)
                    ? getStatusColor(opt.value)
                    : 'text-slate-400 hover:text-slate-200 bg-slate-700/50'"
                  @click="toggleFilter(opt.value)"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>
          </div>

          <!-- Progress Content -->
          <div class="flex-1 flex overflow-hidden">
            <!-- Entry List -->
            <div class="w-80 border-r border-slate-700 overflow-y-auto">
              <div v-if="!selectedCategory" class="p-4 text-center text-slate-400">
                请选择一个分类
              </div>
              <div v-else-if="progressLoading" class="p-4 text-center text-slate-400">
                加载中...
              </div>
              <div v-else-if="entries.length === 0" class="p-4 text-center text-slate-400">
                暂无进度条目
              </div>
              <div v-else class="p-2 space-y-1">
                <div
                  v-for="entry in entries"
                  :key="entry.id"
                  class="p-3 rounded-lg cursor-pointer transition-colors"
                  :class="selectedEntry?.id === entry.id
                    ? 'bg-sky-600/20 border border-sky-600/50'
                    : 'hover:bg-slate-800'"
                  @click="selectEntry(entry)"
                >
                  <div class="flex items-center justify-between mb-1">
                    <span class="text-slate-200 font-medium truncate">{{ entry.name }}</span>
                    <span
                      class="px-2 py-0.5 rounded text-xs"
                      :class="getStatusColor(entry.status)"
                    >
                      {{ getStatusLabel(entry.status) }}
                    </span>
                  </div>
                  <div class="text-xs text-slate-500 truncate">
                    {{ entry.id }}
                  </div>
                  <div v-if="entry.comment" class="text-xs text-slate-400 mt-1 truncate">
                    {{ entry.comment }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Detail Panel -->
            <div class="flex-1 flex flex-col overflow-hidden">
              <div v-if="!selectedEntry" class="flex-1 flex items-center justify-center text-slate-400">
                请选择一个进度条目
              </div>
              <template v-else>
                <!-- Detail Header -->
                <div class="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
                  <h2 class="text-lg font-medium text-slate-100">{{ selectedEntry.name }}</h2>
                  <div class="flex items-center gap-2">
                    <button
                      v-if="!editMode && detailTab === 'info'"
                      class="px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors"
                      @click="startEdit"
                    >
                      编辑
                    </button>
                    <button
                      v-if="!editMode && detailTab === 'info'"
                      class="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 transition-colors"
                      @click="handleDeleteEntry"
                    >
                      删除
                    </button>
                    <template v-if="editMode">
                      <button
                        class="px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors"
                        @click="editMode = false"
                      >
                        取消
                      </button>
                      <button
                        class="px-3 py-1.5 text-sm bg-sky-600 hover:bg-sky-500 text-white rounded transition-colors"
                        @click="saveEdit"
                      >
                        保存
                      </button>
                    </template>
                  </div>
                </div>

                <!-- Detail Tabs -->
                <div class="flex border-b border-slate-700">
                  <button
                    class="px-4 py-2 text-sm transition-colors relative"
                    :class="detailTab === 'info' ? 'text-sky-400' : 'text-slate-400 hover:text-slate-300'"
                    @click="handleDetailTabChange('info')"
                  >
                    基本信息
                    <span
                      v-if="detailTab === 'info'"
                      class="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-400"
                    ></span>
                  </button>
                  <button
                    class="px-4 py-2 text-sm transition-colors relative"
                    :class="detailTab === 'workspace' ? 'text-sky-400' : 'text-slate-400 hover:text-slate-300'"
                    @click="handleDetailTabChange('workspace')"
                  >
                    工作区文件
                    <span
                      v-if="detailTab === 'workspace'"
                      class="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-400"
                    ></span>
                  </button>
                </div>

                <!-- Info Tab Content -->
                <div v-if="detailTab === 'info'" class="flex-1 overflow-y-auto p-6">
                  <!-- View Mode -->
                  <template v-if="!editMode">
                    <div class="space-y-4">
                      <div>
                        <label class="text-sm text-slate-400">ID</label>
                        <p class="text-slate-200 font-mono text-sm mt-1">{{ selectedEntry.id }}</p>
                      </div>

                      <div>
                        <label class="text-sm text-slate-400">状态</label>
                        <div class="flex items-center gap-2 mt-2">
                          <button
                            v-for="opt in statusOptions"
                            :key="opt.value"
                            class="px-3 py-1.5 rounded text-sm transition-colors"
                            :class="selectedEntry.status === opt.value
                              ? getStatusColor(opt.value) + ' ring-1 ring-current'
                              : 'text-slate-400 bg-slate-700/50 hover:bg-slate-700'"
                            @click="quickStatusChange(selectedEntry, opt.value)"
                          >
                            {{ opt.label }}
                          </button>
                        </div>
                      </div>

                      <div v-if="selectedEntry.comment">
                        <label class="text-sm text-slate-400">备注</label>
                        <p class="text-slate-200 mt-1">{{ selectedEntry.comment }}</p>
                      </div>

                      <div v-if="selectedEntry.related_sections.length > 0">
                        <label class="text-sm text-slate-400">关联章节</label>
                        <div class="mt-2 space-y-2">
                          <div
                            v-for="(section, index) in selectedEntry.related_sections"
                            :key="index"
                            class="px-3 py-2 bg-slate-800 rounded text-sm"
                          >
                            <span class="text-sky-400">{{ section.material }}</span>
                            <span class="text-slate-500">:</span>
                            <span class="text-slate-300">{{ section.start_line }}-{{ section.end_line }}</span>
                            <span v-if="section.desc" class="text-slate-400 ml-2">{{ section.desc }}</span>
                          </div>
                        </div>
                      </div>

                      <div v-if="selectedEntry.updated_at">
                        <label class="text-sm text-slate-400">更新时间</label>
                        <p class="text-slate-200 mt-1">{{ new Date(selectedEntry.updated_at).toLocaleString() }}</p>
                      </div>

                      <div v-if="selectedEntry.review_count > 0">
                        <label class="text-sm text-slate-400">复习次数</label>
                        <p class="text-slate-200 mt-1">{{ selectedEntry.review_count }}</p>
                      </div>
                    </div>
                  </template>

                  <!-- Edit Mode -->
                  <template v-else>
                    <div class="space-y-4">
                      <div>
                        <label class="text-sm text-slate-400">状态</label>
                        <select
                          v-model="editData.status"
                          class="mt-2 w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded text-slate-200 focus:outline-none focus:border-sky-500"
                        >
                          <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                            {{ opt.label }}
                          </option>
                        </select>
                      </div>

                      <div>
                        <label class="text-sm text-slate-400">备注</label>
                        <textarea
                          v-model="editData.comment"
                          rows="4"
                          class="mt-2 w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded text-slate-200 focus:outline-none focus:border-sky-500 resize-none"
                          placeholder="添加备注..."
                        />
                      </div>
                    </div>
                  </template>
                </div>

                <!-- Workspace Tab Content -->
                <div v-if="detailTab === 'workspace'" class="flex-1 flex overflow-hidden">
                  <!-- File List -->
                  <div class="w-48 flex-shrink-0 border-r border-slate-700 overflow-y-auto">
                    <div v-if="workspaceLoading && workspaceFiles.length === 0" class="p-3 text-sm text-slate-400">
                      加载中...
                    </div>
                    <div v-else-if="workspaceFiles.length === 0" class="p-3 text-sm text-slate-500">
                      暂无文件
                    </div>
                    <div v-else class="py-1">
                      <div
                        v-for="file in workspaceFiles"
                        :key="file.path"
                        class="group px-3 py-2 cursor-pointer transition-colors flex items-center justify-between"
                        :class="selectedWorkspaceFile === file.path ? 'bg-sky-600/20 text-sky-400' : 'text-slate-300 hover:bg-slate-800'"
                        @click="selectWorkspaceFile(file.path)"
                      >
                        <div class="flex items-center gap-2 min-w-0 flex-1">
                          <span>{{ getFileIcon(file.path) }}</span>
                          <span class="truncate text-sm">{{ file.path }}</span>
                        </div>
                        <button
                          class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-1 flex-shrink-0"
                          title="删除文件"
                          @click.stop="handleDeleteWorkspaceFile(file.path)"
                        >
                          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>

                  <!-- File Content -->
                  <div class="flex-1 overflow-y-auto">
                    <div v-if="workspaceLoading" class="p-4 text-slate-400">
                      加载中...
                    </div>
                    <div v-else-if="!selectedWorkspaceFile" class="p-4 text-slate-500">
                      选择一个文件查看内容
                    </div>
                    <div v-else-if="isMarkdownFile(selectedWorkspaceFile)" class="p-4">
                      <MarkdownViewer :content="workspaceFileContent" />
                    </div>
                    <div v-else class="p-4">
                      <pre class="text-sm text-slate-300 whitespace-pre-wrap font-mono bg-slate-800 rounded p-4 overflow-x-auto">{{ workspaceFileContent }}</pre>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>

        <!-- Task Progress Panel -->
        <div class="flex-shrink-0">
          <TaskProgressPanel
            ref="taskPanel"
            v-model:collapsed="taskPanelCollapsed"
            @task-complete="handleTaskComplete"
          />
        </div>
      </div>
    </div>

    <!-- New Category Modal -->
    <Teleport to="body">
      <div
        v-if="showNewCategoryModal"
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        @click.self="showNewCategoryModal = false"
      >
        <div class="bg-slate-800 rounded-lg p-6 w-96 shadow-xl">
          <h3 class="text-lg font-medium text-slate-200 mb-4">新建分类</h3>
          <input
            v-model="newCategoryName"
            type="text"
            class="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-sky-500"
            placeholder="输入分类名称"
            @keyup.enter="handleCreateCategory"
          />
          <div class="flex justify-end gap-3 mt-4">
            <button
              class="px-4 py-2 text-sm text-slate-400 hover:text-slate-300"
              @click="showNewCategoryModal = false"
            >
              取消
            </button>
            <button
              class="px-4 py-2 text-sm bg-sky-500 text-white rounded hover:bg-sky-600 disabled:opacity-50"
              :disabled="!newCategoryName.trim()"
              @click="handleCreateCategory"
            >
              创建
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.category-manager {
  background: rgb(15 23 42);
}
</style>
