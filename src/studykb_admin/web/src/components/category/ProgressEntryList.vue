<script setup lang="ts">
import { useProgressStore, getStatusColor, getStatusLabel } from '../../stores/useProgressStore'
import AppSkeleton from '../ui/AppSkeleton.vue'
import AppEmptyState from '../ui/AppEmptyState.vue'

const progressStore = useProgressStore()

defineProps<{
  categoryName: string | null
}>()
</script>

<template>
  <div class="flex-1 overflow-y-auto">
    <!-- No category -->
    <div v-if="!categoryName" class="h-full flex items-center justify-center">
      <AppEmptyState icon="folder" title="请选择一个分类" />
    </div>

    <!-- Loading -->
    <AppSkeleton v-else-if="progressStore.loading" type="list" :count="5" />

    <!-- Empty -->
    <div v-else-if="progressStore.entries.length === 0" class="h-full flex items-center justify-center">
      <AppEmptyState
        icon="chart"
        title="暂无进度条目"
        description="请先在「资料管理」中上传资料并初始化进度"
      />
    </div>

    <!-- Entry list -->
    <div v-else class="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      <div
        v-for="entry in progressStore.sortedEntries"
        :key="entry.id"
        class="p-3 rounded-lg cursor-pointer transition-colors"
        :class="progressStore.selectedEntry?.id === entry.id
          ? 'bg-sky-600/20 border border-sky-600/50'
          : 'hover:bg-slate-800/70 border border-transparent'"
        @click="progressStore.selectEntry(entry)"
      >
        <div class="flex items-center justify-between mb-1">
          <span class="text-slate-200 font-medium truncate text-sm">{{ entry.name }}</span>
          <span
            class="px-2 py-0.5 rounded text-xs flex-shrink-0 ml-2"
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
</template>
