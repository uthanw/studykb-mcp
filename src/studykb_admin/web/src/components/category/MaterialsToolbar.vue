<script setup lang="ts">
import { useCategoryStore } from '../../stores/useCategoryStore'

const store = useCategoryStore()

const emit = defineEmits<{
  upload: [event: Event]
  'generate-index': []
  'init-progress': []
}>()
</script>

<template>
  <div class="flex-shrink-0 px-5 py-3.5 border-b border-slate-700 flex items-center gap-3 flex-wrap">
    <label
      class="px-3 py-1.5 text-sm bg-sky-500/20 text-sky-400 rounded-lg cursor-pointer hover:bg-sky-500/30 transition-colors flex items-center gap-1.5"
      :class="{ 'opacity-50 cursor-not-allowed': !store.selectedCategoryName || store.uploading }"
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
        :disabled="!store.selectedCategoryName || store.uploading"
        @change="emit('upload', $event)"
      />
    </label>

    <button
      class="px-3 py-1.5 text-sm bg-amber-500/20 text-amber-400 rounded-lg hover:bg-amber-500/30 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="!store.hasSelectedMaterials"
      @click="emit('generate-index')"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
      生成索引
    </button>

    <button
      class="px-3 py-1.5 text-sm bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="!store.selectedCategoryName"
      @click="emit('init-progress')"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
      初始化进度
    </button>

    <div v-if="store.uploadProgress" class="text-sm text-slate-400">
      {{ store.uploadProgress }}
    </div>

    <div class="flex-1"></div>

    <button
      v-if="store.materials.length > 0"
      class="text-xs text-slate-400 hover:text-slate-300 transition-colors"
      @click="store.selectAllMaterials()"
    >
      {{ store.selectedMaterials.size === store.materials.length ? '取消全选' : '全选' }}
    </button>
  </div>
</template>
