<script setup lang="ts">
import { type FileVersion } from '../api'
import AppSkeleton from './ui/AppSkeleton.vue'

defineProps<{
  versions: FileVersion[]
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'view', version: FileVersion): void
  (e: 'rollback', version: FileVersion): void
}>()

const OP_CONFIG: Record<string, { label: string; color: string; dotColor: string }> = {
  create: { label: '创建', color: 'text-emerald-400', dotColor: 'bg-emerald-500' },
  write: { label: '覆写', color: 'text-sky-400', dotColor: 'bg-sky-500' },
  edit: { label: '编辑', color: 'text-amber-400', dotColor: 'bg-amber-500' },
  delete: { label: '删除', color: 'text-red-400', dotColor: 'bg-red-500' },
}

function getOpConfig(op: string) {
  return OP_CONFIG[op] || { label: op, color: 'text-slate-400', dotColor: 'bg-slate-500' }
}

function formatTime(ts: string): string {
  try {
    const d = new Date(ts)
    const pad = (n: number) => String(n).padStart(2, '0')
    const month = d.getMonth() + 1
    const day = d.getDate()
    const hour = pad(d.getHours())
    const min = pad(d.getMinutes())
    const sec = pad(d.getSeconds())
    return `${month}/${day} ${hour}:${min}:${sec}`
  } catch {
    return ts
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="px-3 py-2.5 border-b border-slate-700 flex items-center justify-between">
      <span class="text-xs font-medium text-slate-400">版本历史</span>
      <span class="text-xs text-slate-600">{{ versions.length }} 个版本</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="p-3">
      <AppSkeleton type="list" :count="4" />
    </div>

    <!-- Empty -->
    <div v-else-if="versions.length === 0" class="flex-1 flex items-center justify-center p-4">
      <div class="text-center">
        <svg class="w-8 h-8 mx-auto mb-2 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p class="text-xs text-slate-500">暂无历史记录</p>
        <p class="text-xs text-slate-600 mt-1">文件被 MCP 工具操作后<br>会自动记录版本</p>
      </div>
    </div>

    <!-- Timeline -->
    <div v-else class="flex-1 overflow-y-auto">
      <div class="relative py-2">
        <!-- Vertical line -->
        <div class="absolute left-[19px] top-4 bottom-4 w-px bg-slate-700" />

        <!-- Version items -->
        <div
          v-for="(version, idx) in versions"
          :key="version.version_id"
          class="group relative pl-10 pr-3 py-2.5 hover:bg-slate-800/50 transition-colors"
        >
          <!-- Dot -->
          <div
            class="absolute left-3.5 top-4 w-2.5 h-2.5 rounded-full ring-2 ring-slate-900"
            :class="getOpConfig(version.operation).dotColor"
          />

          <!-- Content -->
          <div class="flex flex-col gap-1">
            <!-- Operation + time -->
            <div class="flex items-center gap-2">
              <span
                class="text-xs font-medium"
                :class="getOpConfig(version.operation).color"
              >
                {{ getOpConfig(version.operation).label }}
              </span>
              <span class="text-xs text-slate-500">{{ formatTime(version.timestamp) }}</span>
            </div>

            <!-- Description -->
            <p v-if="version.description" class="text-xs text-slate-400 leading-relaxed">
              {{ version.description }}
            </p>

            <!-- Meta -->
            <div class="flex items-center gap-3 text-xs text-slate-600">
              <span>{{ version.lines }} 行</span>
              <span>{{ formatSize(version.size) }}</span>
            </div>

            <!-- Actions (hover) -->
            <div class="flex gap-2 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                class="px-2 py-0.5 text-xs rounded bg-slate-700 text-sky-400 hover:bg-slate-600 transition-colors"
                @click="emit('view', version)"
              >
                对比
              </button>
              <button
                v-if="idx > 0 || version.operation !== 'create'"
                class="px-2 py-0.5 text-xs rounded bg-slate-700 text-amber-400 hover:bg-slate-600 transition-colors"
                @click="emit('rollback', version)"
              >
                回滚
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
