<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  fetchCategories,
  createCategory,
  deleteCategory,
  deleteMaterial,
  uploadMaterial,
  generateIndex,
  initProgress,
  type Category,
} from '../api'
import McpConfigBox from '../components/McpConfigBox.vue'
import TaskProgressPanel from '../components/TaskProgressPanel.vue'

// State
const categories = ref<Category[]>([])
const selectedCategory = ref<string | null>(null)
const selectedMaterials = ref<Set<string>>(new Set())
const loading = ref(true)
const error = ref<string | null>(null)
const showNewCategoryModal = ref(false)
const newCategoryName = ref('')
const uploading = ref(false)
const uploadProgress = ref<string | null>(null)
const taskPanel = ref<InstanceType<typeof TaskProgressPanel> | null>(null)
const mcpCollapsed = ref(true)
const taskPanelCollapsed = ref(true)

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
}
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

              <!-- Selection indicator -->
              <div
                class="absolute top-2 left-2 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors"
                :class="selectedMaterials.has(mat.name) ? 'bg-sky-500 border-sky-500' : 'border-slate-600'"
                style="position: absolute; display: none;"
              >
                <svg v-if="selectedMaterials.has(mat.name)" class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
          </div>
        </div>

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
