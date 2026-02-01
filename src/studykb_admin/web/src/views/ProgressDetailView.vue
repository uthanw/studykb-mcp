<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchProgress, updateProgress, deleteProgress, initProgress, type ProgressEntry, type ProgressStats } from '@/api'
import TaskProgressPanel from '@/components/TaskProgressPanel.vue'

const route = useRoute()
const router = useRouter()
const category = computed(() => route.params.category as string)
const taskPanel = ref<InstanceType<typeof TaskProgressPanel> | null>(null)
const taskPanelCollapsed = ref(true)

const entries = ref<ProgressEntry[]>([])
const stats = ref<ProgressStats | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const selectedEntry = ref<ProgressEntry | null>(null)
const statusFilter = ref<string[]>([])
const editMode = ref(false)
const editData = ref({
  status: '',
  comment: '',
})

const statusOptions = [
  { value: 'pending', label: '待学', color: 'slate' },
  { value: 'active', label: '进行中', color: 'sky' },
  { value: 'review', label: '复习', color: 'amber' },
  { value: 'done', label: '完成', color: 'green' },
]

async function loadProgress() {
  loading.value = true
  error.value = null
  try {
    const data = await fetchProgress(category.value, statusFilter.value.length > 0 ? statusFilter.value : undefined)
    entries.value = data.entries
    stats.value = data.stats
  } catch (e: any) {
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

async function saveEdit() {
  if (!selectedEntry.value) return

  try {
    await updateProgress(category.value, selectedEntry.value.id, {
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

async function handleDelete() {
  if (!selectedEntry.value) return
  if (!confirm(`确定删除进度条目 "${selectedEntry.value.name}"？`)) return

  try {
    await deleteProgress(category.value, selectedEntry.value.id)
    selectedEntry.value = null
    await loadProgress()
  } catch (e: any) {
    error.value = e.message
  }
}

async function quickStatusChange(entry: ProgressEntry, newStatus: string) {
  try {
    await updateProgress(category.value, entry.id, {
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

function goBack() {
  router.push('/progress')
}

async function handleInitProgress() {
  const sessionId = taskPanel.value?.getSessionId() || ''
  taskPanel.value?.startTask('初始化进度')
  taskPanel.value?.connect()

  try {
    await initProgress(category.value, sessionId)
  } catch (e: any) {
    error.value = e.message
  }
}

function handleTaskComplete() {
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

onMounted(loadProgress)
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <header class="px-6 py-4 border-b border-slate-700">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <button
            class="p-2 text-slate-400 hover:text-slate-200 transition-colors"
            @click="goBack"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 class="text-xl font-semibold text-slate-100">{{ category }} 进度</h1>
            <p v-if="stats" class="text-sm text-slate-400 mt-1">
              待学 {{ stats.pending }} · 进行中 {{ stats.active }} · 复习 {{ stats.review }} · 完成 {{ stats.done }}
            </p>
          </div>
        </div>
        <button
          class="px-3 py-1.5 text-sm bg-green-500/20 text-green-400 rounded hover:bg-green-500/30 transition-colors flex items-center gap-1.5"
          @click="handleInitProgress"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          初始化进度
        </button>
      </div>
    </header>

    <!-- Filters -->
    <div class="px-6 py-3 border-b border-slate-700 flex items-center gap-2">
      <span class="text-sm text-slate-400 mr-2">筛选:</span>
      <button
        v-for="opt in statusOptions"
        :key="opt.value"
        class="px-3 py-1 rounded-full text-sm transition-colors"
        :class="statusFilter.includes(opt.value)
          ? getStatusColor(opt.value)
          : 'text-slate-400 hover:text-slate-200 bg-slate-700/50'"
        @click="toggleFilter(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>

    <!-- Content -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Entry List -->
      <div class="w-80 border-r border-slate-700 overflow-y-auto">
        <div v-if="loading" class="p-4 text-center text-slate-400">
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
                v-if="!editMode"
                class="px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors"
                @click="startEdit"
              >
                编辑
              </button>
              <button
                v-if="!editMode"
                class="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 transition-colors"
                @click="handleDelete"
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

          <!-- Detail Content -->
          <div class="flex-1 overflow-y-auto p-6">
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
        </template>
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
</template>
