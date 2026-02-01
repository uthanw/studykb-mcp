<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api'

interface McpConfig {
  mcpServers: {
    studykb: {
      command: string
      args: string[]
      env: Record<string, string>
    }
  }
}

const props = defineProps<{
  collapsed?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:collapsed', value: boolean): void
}>()

const isCollapsed = ref(props.collapsed ?? false)
const config = ref<McpConfig | null>(null)
const copied = ref(false)
const loading = ref(true)
const error = ref<string | null>(null)

async function loadConfig() {
  loading.value = true
  error.value = null
  try {
    const response = await api.get('/config/mcp')
    config.value = response.data
  } catch (e: any) {
    error.value = e.message || '加载配置失败'
  } finally {
    loading.value = false
  }
}

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
  emit('update:collapsed', isCollapsed.value)
}

async function copyConfig() {
  if (!config.value) return

  try {
    await navigator.clipboard.writeText(JSON.stringify(config.value, null, 2))
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (e) {
    // Fallback for older browsers
    const textarea = document.createElement('textarea')
    textarea.value = JSON.stringify(config.value, null, 2)
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<template>
  <div class="mcp-config-box bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
    <!-- Header -->
    <div
      class="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-slate-700/50 transition-colors"
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
        <svg class="w-5 h-5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <span class="text-sm font-medium text-slate-200">MCP 服务器配置</span>
      </div>
      <button
        v-if="!isCollapsed && config"
        class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors"
        :class="copied
          ? 'bg-green-500/20 text-green-400'
          : 'bg-sky-500/20 text-sky-400 hover:bg-sky-500/30'"
        @click.stop="copyConfig"
      >
        <svg v-if="copied" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        {{ copied ? '已复制' : '复制配置' }}
      </button>
    </div>

    <!-- Content -->
    <div v-show="!isCollapsed" class="border-t border-slate-700">
      <!-- Loading -->
      <div v-if="loading" class="p-4 text-center text-slate-400">
        <svg class="animate-spin h-5 w-5 mx-auto mb-2" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        加载中...
      </div>

      <!-- Error -->
      <div v-else-if="error" class="p-4 text-center text-red-400">
        <p>{{ error }}</p>
        <button
          class="mt-2 text-sm text-sky-400 hover:text-sky-300"
          @click="loadConfig"
        >
          重试
        </button>
      </div>

      <!-- Config JSON -->
      <div v-else-if="config" class="p-4">
        <p class="text-xs text-slate-400 mb-2">
          将以下配置添加到你的 Claude Code 或其他 MCP 客户端中：
        </p>
        <pre class="bg-slate-900 rounded-md p-3 text-xs text-slate-300 overflow-x-auto font-mono">{{ JSON.stringify(config, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>
