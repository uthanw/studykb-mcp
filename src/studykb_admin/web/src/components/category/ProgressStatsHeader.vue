<script setup lang="ts">
import { useProgressStore, statusOptions, getStatusColor } from '../../stores/useProgressStore'

const progressStore = useProgressStore()

defineProps<{
  categoryName: string
}>()
</script>

<template>
  <div class="flex-shrink-0 px-5 py-3.5 border-b border-slate-700">
    <div class="flex items-center justify-between">
      <div v-if="progressStore.stats" class="text-sm text-slate-400">
        待学 <span class="text-slate-200 font-medium">{{ progressStore.stats.pending }}</span> ·
        进行中 <span class="text-sky-400 font-medium">{{ progressStore.stats.active }}</span> ·
        复习 <span class="text-amber-400 font-medium">{{ progressStore.stats.review }}</span> ·
        完成 <span class="text-green-400 font-medium">{{ progressStore.stats.done }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-sm text-slate-500">筛选:</span>
        <button
          v-for="opt in statusOptions"
          :key="opt.value"
          class="px-2.5 py-1 rounded-lg text-xs transition-colors"
          :class="progressStore.statusFilter.includes(opt.value)
            ? getStatusColor(opt.value)
            : 'text-slate-400 hover:text-slate-200 bg-slate-700/50'"
          @click="progressStore.toggleFilter(opt.value, categoryName)"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>
  </div>
</template>
