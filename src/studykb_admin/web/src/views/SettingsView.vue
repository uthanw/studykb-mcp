<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getTasksConfigStatus } from '../api'

interface ConfigStatus {
  llm: {
    configured: boolean
    model: string
    base_url: string
  }
  mineru: {
    configured: boolean
    model_version: string
  }
}

const configStatus = ref<ConfigStatus | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function loadConfig() {
  loading.value = true
  error.value = null
  try {
    configStatus.value = await getTasksConfigStatus()
  } catch (e: any) {
    error.value = e.message || '加载配置失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadConfig)
</script>

<template>
  <div class="settings-view h-full overflow-y-auto">
    <div class="max-w-2xl mx-auto p-6">
      <h1 class="text-2xl font-semibold text-slate-100 mb-6">设置</h1>

      <!-- Loading -->
      <div v-if="loading" class="text-center text-slate-400 py-8">
        加载中...
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-center text-red-400 py-8">
        {{ error }}
        <button class="block mx-auto mt-4 text-sky-400 hover:text-sky-300" @click="loadConfig">
          重试
        </button>
      </div>

      <!-- Config Status -->
      <div v-else-if="configStatus" class="space-y-6">
        <!-- LLM Config -->
        <div class="bg-slate-800 rounded-lg p-6">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-medium text-slate-200">LLM API 配置</h2>
            <span
              class="px-2 py-1 text-xs rounded"
              :class="configStatus.llm.configured ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'"
            >
              {{ configStatus.llm.configured ? '已配置' : '未配置' }}
            </span>
          </div>

          <div class="space-y-3 text-sm">
            <div class="flex items-center justify-between">
              <span class="text-slate-400">模型</span>
              <span class="text-slate-200 font-mono">{{ configStatus.llm.model || '-' }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-400">API Base URL</span>
              <span class="text-slate-200 font-mono text-xs">{{ configStatus.llm.base_url || '-' }}</span>
            </div>
          </div>

          <div class="mt-4 pt-4 border-t border-slate-700">
            <p class="text-xs text-slate-500">
              LLM API 用于生成索引和初始化进度。请在配置文件中设置 API 密钥。
            </p>
            <p class="text-xs text-slate-500 mt-2">
              配置文件路径: <code class="text-slate-400">~/.studykb/config.toml</code>
            </p>
          </div>
        </div>

        <!-- MinerU Config -->
        <div class="bg-slate-800 rounded-lg p-6">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-medium text-slate-200">MinerU API 配置</h2>
            <span
              class="px-2 py-1 text-xs rounded"
              :class="configStatus.mineru.configured ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'"
            >
              {{ configStatus.mineru.configured ? '已配置' : '未配置' }}
            </span>
          </div>

          <div class="space-y-3 text-sm">
            <div class="flex items-center justify-between">
              <span class="text-slate-400">模型版本</span>
              <span class="text-slate-200 font-mono">{{ configStatus.mineru.model_version || '-' }}</span>
            </div>
          </div>

          <div class="mt-4 pt-4 border-t border-slate-700">
            <p class="text-xs text-slate-500">
              MinerU API 用于将 PDF/Word/PPT 文件转换为 Markdown。
            </p>
            <p class="text-xs text-slate-500 mt-2">
              配置文件路径: <code class="text-slate-400">~/.studykb/config.toml</code>
            </p>
          </div>
        </div>

        <!-- Config File Example -->
        <div class="bg-slate-800 rounded-lg p-6">
          <h2 class="text-lg font-medium text-slate-200 mb-4">配置文件示例</h2>
          <pre class="bg-slate-900 rounded p-4 text-xs text-slate-300 overflow-x-auto font-mono">
[llm]
api_key = "sk-xxx"
base_url = "https://api.openai.com/v1"
model = "gpt-4o-mini"

[mineru]
api_key = "your-mineru-api-key"
model_version = "2024-09-18"
          </pre>
        </div>

        <!-- About -->
        <div class="bg-slate-800 rounded-lg p-6">
          <h2 class="text-lg font-medium text-slate-200 mb-4">关于</h2>
          <div class="space-y-2 text-sm text-slate-400">
            <p>StudyKB Admin - 知识库管理界面</p>
            <p>版本: 0.1.0</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  background: rgb(15 23 42);
}
</style>
