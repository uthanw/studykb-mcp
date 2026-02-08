<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { cancelTask } from '../api'

interface TaskLog {
  type: 'log' | 'status' | 'progress' | 'tool_call' | 'tool_result' | 'error' | 'complete'
  content: string
  timestamp: Date
  active?: boolean
  step?: number
  total?: number
}

interface Task {
  id: string
  name: string
  status: 'running' | 'completed' | 'failed'
  logs: TaskLog[]
}

const props = defineProps<{
  sessionId?: string
  collapsed?: boolean
}>()

const emit = defineEmits<{
  (e: 'task-complete', taskId: string, success: boolean): void
  (e: 'update:collapsed', value: boolean): void
}>()

const isCollapsed = ref(props.collapsed ?? true)
const tasks = ref<Task[]>([])
const ws = ref<WebSocket | null>(null)
const logContainer = ref<HTMLElement | null>(null)

// Use persistent session ID from localStorage
const STORAGE_KEY = 'studykb_session_id'

function getOrCreateSessionId(): string {
  if (props.sessionId) return props.sessionId

  let stored = localStorage.getItem(STORAGE_KEY)
  if (!stored) {
    stored = Math.random().toString(36).substring(2, 10)
    localStorage.setItem(STORAGE_KEY, stored)
  }
  return stored
}

const sessionId = ref(getOrCreateSessionId())

// Connect WebSocket
function connect() {
  if (ws.value?.readyState === WebSocket.OPEN) return

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/tasks/ws/${sessionId.value}`

  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
    console.log('TaskProgressPanel: WebSocket connected')
  }

  ws.value.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    handleMessage(msg)
  }

  ws.value.onclose = () => {
    console.log('TaskProgressPanel: WebSocket closed')
    // Auto-reconnect after 2 seconds
    setTimeout(() => {
      if (tasks.value.some(t => t.status === 'running')) {
        connect()
      }
    }, 2000)
  }

  ws.value.onerror = (error) => {
    console.error('TaskProgressPanel: WebSocket error', error)
  }
}

// Handle WebSocket message
function handleMessage(msg: any) {
  // Find or create current task
  let currentTask = tasks.value.find(t => t.status === 'running')
  if (!currentTask) {
    currentTask = {
      id: Math.random().toString(36).substring(2, 10),
      name: '任务',
      status: 'running',
      logs: [],
    }
    tasks.value.unshift(currentTask)
  }

  const log: TaskLog = {
    type: msg.type,
    content: msg.content,
    timestamp: new Date(),
  }

  if (msg.type === 'progress') {
    log.step = msg.step
    log.total = msg.total
  }

  if (msg.type === 'status') {
    log.active = msg.active
  }

  currentTask.logs.push(log)

  // Handle completion
  if (msg.type === 'complete') {
    currentTask.status = msg.success ? 'completed' : 'failed'
    emit('task-complete', currentTask.id, msg.success)
  }

  if (msg.type === 'error') {
    currentTask.status = 'failed'
    emit('task-complete', currentTask.id, false)
  }

  // Auto-expand when receiving messages
  if (isCollapsed.value) {
    isCollapsed.value = false
    emit('update:collapsed', false)
  }

  scrollToBottom()
}

// Start a new task
function startTask(name: string) {
  const task: Task = {
    id: Math.random().toString(36).substring(2, 10),
    name,
    status: 'running',
    logs: [],
  }
  tasks.value.unshift(task)
  connect()
  isCollapsed.value = false
  emit('update:collapsed', false)
  return task.id
}

// Clear completed tasks
function clearCompleted() {
  tasks.value = tasks.value.filter(t => t.status === 'running')
}

// Cancel running task
const cancelling = ref(false)
async function cancelRunningTask() {
  cancelling.value = true
  try {
    // Send cancel via WebSocket
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type: 'cancel' }))
    }
    // Also call HTTP endpoint as backup
    await cancelTask(sessionId.value)
  } catch (e) {
    console.error('Cancel failed:', e)
  } finally {
    cancelling.value = false
  }
}

// Scroll to bottom
function scrollToBottom() {
  setTimeout(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  }, 50)
}

// Toggle collapse
function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
  emit('update:collapsed', isCollapsed.value)
}

// Get session ID for API calls
function getSessionId() {
  return sessionId.value
}

// Expose methods
defineExpose({
  startTask,
  clearCompleted,
  getSessionId,
  connect,
})

watch(() => props.collapsed, (val) => {
  isCollapsed.value = val ?? true
})

onMounted(() => {
  // Auto-connect to receive any ongoing task progress
  connect()
})

onUnmounted(() => {
  if (ws.value) {
    ws.value.close()
  }
})
</script>

<template>
  <div class="task-progress-panel bg-slate-900 border-t border-slate-700">
    <!-- Header -->
    <div
      class="px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-slate-800/50 transition-colors"
      @click="toggleCollapse"
    >
      <div class="flex items-center gap-2">
        <svg
          class="w-4 h-4 text-slate-400 transition-transform"
          :class="{ '-rotate-90': isCollapsed }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
        <span class="text-sm font-medium text-slate-300">任务进度</span>
        <span v-if="tasks.some(t => t.status === 'running')" class="flex items-center gap-1">
          <span class="w-2 h-2 bg-sky-400 rounded-full animate-pulse"></span>
          <span class="text-xs text-sky-400">运行中</span>
        </span>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="tasks.some(t => t.status === 'running')"
          class="text-xs text-red-400 hover:text-red-300 transition-colors px-1.5 py-0.5 rounded hover:bg-red-500/10"
          :disabled="cancelling"
          @click.stop="cancelRunningTask"
        >
          {{ cancelling ? '中断中...' : '中断任务' }}
        </button>
        <button
          v-if="tasks.some(t => t.status !== 'running')"
          class="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          @click.stop="clearCompleted"
        >
          清除已完成
        </button>
      </div>
    </div>

    <!-- Content -->
    <div
      v-show="!isCollapsed"
      ref="logContainer"
      class="max-h-64 overflow-y-auto"
    >
      <div v-if="tasks.length === 0" class="px-4 py-8 text-center text-slate-500 text-sm">
        暂无任务
      </div>
      <div v-else class="divide-y divide-slate-800">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="px-4 py-3"
        >
          <!-- Task header -->
          <div class="flex items-center gap-2 mb-2">
            <span
              v-if="task.status === 'running'"
              class="w-4 h-4 border-2 border-sky-400 border-t-transparent rounded-full animate-spin"
            ></span>
            <span v-else-if="task.status === 'completed'" class="text-green-400">✓</span>
            <span v-else class="text-red-400">✗</span>
            <span class="text-sm font-medium text-slate-200">{{ task.name }}</span>
          </div>

          <!-- Task logs -->
          <div class="space-y-1 font-mono text-xs">
            <div
              v-for="(log, index) in task.logs.slice(-10)"
              :key="index"
              :class="{
                'text-slate-400': log.type === 'log',
                'text-sky-400': log.type === 'status' || log.type === 'progress',
                'text-amber-400': log.type === 'tool_call',
                'text-green-400': log.type === 'complete',
                'text-red-400': log.type === 'error',
              }"
            >
              <span v-if="log.type === 'progress'" class="mr-2">[{{ log.step }}/{{ log.total }}]</span>
              <span v-if="log.type === 'status' && log.active" class="animate-pulse">⏳ </span>
              {{ log.content }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
