<script setup lang="ts">
import { useCategoryStore } from '../../stores/useCategoryStore'
import AppSkeleton from '../ui/AppSkeleton.vue'
import AppEmptyState from '../ui/AppEmptyState.vue'

const store = useCategoryStore()

const emit = defineEmits<{
  'new-category': []
  'select': [name: string]
}>()

function handleSelect(name: string) {
  emit('select', name)
}
</script>

<template>
  <div class="w-64 flex-shrink-0 border-r border-slate-700 flex flex-col">
    <div class="px-4 py-3.5 border-b border-slate-700 flex items-center justify-between">
      <span class="text-sm font-medium text-slate-300">分类列表</span>
      <button
        class="text-xs px-2.5 py-1 bg-sky-500/20 text-sky-400 rounded-lg hover:bg-sky-500/30 transition-colors"
        @click="emit('new-category')"
      >
        + 新建
      </button>
    </div>

    <div class="flex-1 overflow-y-auto">
      <AppSkeleton v-if="store.loading" type="list" :count="4" />

      <div v-else-if="store.error" class="p-4 text-center text-red-400 text-sm">
        {{ store.error }}
      </div>

      <AppEmptyState
        v-else-if="store.categories.length === 0"
        icon="folder"
        title="暂无分类"
        description="创建第一个分类开始管理学习资料"
        action-text="+ 新建分类"
        @action="emit('new-category')"
      />

      <div v-else class="py-2">
        <div
          v-for="cat in store.categories"
          :key="cat.name"
          class="group px-4 py-2.5 cursor-pointer transition-colors flex items-center justify-between border-l-2"
          :class="store.selectedCategoryName === cat.name
            ? 'bg-sky-500/10 text-sky-400 border-sky-400'
            : 'text-slate-300 hover:bg-slate-800/70 border-transparent'"
          @click="handleSelect(cat.name)"
        >
          <div class="flex items-center gap-2.5 min-w-0">
            <span class="text-lg opacity-70">📁</span>
            <span class="truncate text-sm">{{ cat.name }}</span>
            <span class="text-xs text-slate-500">({{ cat.file_count }})</span>
          </div>
          <button
            class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-1 transition-opacity"
            title="删除分类"
            @click.stop="store.remove(cat.name)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
