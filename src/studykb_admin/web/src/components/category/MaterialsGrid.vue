<script setup lang="ts">
import { ref } from 'vue'
import { useCategoryStore } from '../../stores/useCategoryStore'
import AppEmptyState from '../ui/AppEmptyState.vue'

const store = useCategoryStore()

const emit = defineEmits<{
  drop: [event: DragEvent]
}>()

const isDragOver = ref(false)
let dragCounter = 0

function handleDragEnter(event: DragEvent) {
  event.preventDefault()
  dragCounter++
  isDragOver.value = true
}

function handleDragLeave(event: DragEvent) {
  event.preventDefault()
  dragCounter--
  if (dragCounter === 0) {
    isDragOver.value = false
  }
}

function handleDragOver(event: DragEvent) {
  event.preventDefault()
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  isDragOver.value = false
  dragCounter = 0
  emit('drop', event)
}
</script>

<template>
  <div
    class="flex-1 overflow-y-auto p-5 relative"
    @drop="handleDrop"
    @dragover="handleDragOver"
    @dragenter="handleDragEnter"
    @dragleave="handleDragLeave"
  >
    <!-- Drag overlay -->
    <div
      v-if="isDragOver && store.selectedCategoryName"
      class="absolute inset-0 z-10 bg-sky-500/5 border-2 border-dashed border-sky-400/50 rounded-lg flex items-center justify-center pointer-events-none"
    >
      <div class="flex flex-col items-center gap-2">
        <svg class="w-10 h-10 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        <span class="text-sm text-sky-400 font-medium">松开以上传文件</span>
      </div>
    </div>

    <!-- No category selected -->
    <div v-if="!store.selectedCategoryName" class="h-full flex items-center justify-center">
      <AppEmptyState
        icon="folder"
        title="请选择一个分类"
        description="从左侧选择一个分类来管理其中的资料"
      />
    </div>

    <!-- Empty materials -->
    <div v-else-if="store.materials.length === 0" class="h-full flex items-center justify-center">
      <AppEmptyState
        icon="file"
        title="暂无资料"
        description="拖拽文件到此处上传，或点击上方「上传资料」按钮。支持格式: .md, .pdf, .doc, .docx, .ppt, .pptx"
      />
    </div>

    <!-- Materials grid -->
    <div
      v-else
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
    >
      <div
        v-for="mat in store.materials"
        :key="mat.name"
        class="bg-slate-800 rounded-lg p-5 border-2 cursor-pointer group transition-colors"
        :class="store.selectedMaterials.has(mat.name) ? 'border-sky-500' : 'border-transparent hover:border-slate-600'"
        @click="store.toggleMaterial(mat.name)"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0 flex-1">
            <div class="font-medium text-slate-200 truncate" :title="mat.name">
              {{ mat.name.replace('.md', '') }}
            </div>
            <div class="text-xs text-slate-500 mt-1.5">
              {{ mat.line_count.toLocaleString() }} 行
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span
              v-if="mat.has_index"
              class="text-xs px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded cursor-pointer hover:bg-green-500/30 transition-colors"
              title="查看索引"
              @click.stop="store.previewIndex(mat.name)"
            >
              索引
            </span>
            <button
              class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-1 transition-opacity"
              title="删除资料"
              @click.stop="store.removeMaterial(mat.name)"
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
