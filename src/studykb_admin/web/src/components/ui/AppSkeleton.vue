<script setup lang="ts">
withDefaults(defineProps<{
  type?: 'list' | 'card' | 'detail' | 'text'
  count?: number
}>(), {
  type: 'list',
  count: 3,
})
</script>

<template>
  <!-- List skeleton -->
  <div v-if="type === 'list'" class="space-y-3 p-3">
    <div
      v-for="i in count"
      :key="i"
      class="animate-pulse flex items-center gap-3 p-3 rounded-lg"
    >
      <div class="w-8 h-8 bg-slate-700/50 rounded-lg flex-shrink-0" />
      <div class="flex-1 space-y-2">
        <div class="h-4 bg-slate-700/50 rounded w-3/4" />
        <div class="h-3 bg-slate-700/30 rounded w-1/2" />
      </div>
    </div>
  </div>

  <!-- Card skeleton -->
  <div v-else-if="type === 'card'" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
    <div
      v-for="i in count"
      :key="i"
      class="animate-pulse bg-slate-800 rounded-lg p-5 border border-slate-700/30"
    >
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1 space-y-2">
          <div class="h-4 bg-slate-700/50 rounded w-3/4" />
          <div class="h-3 bg-slate-700/30 rounded w-1/3" />
        </div>
        <div class="w-12 h-5 bg-slate-700/30 rounded" />
      </div>
    </div>
  </div>

  <!-- Detail skeleton -->
  <div v-else-if="type === 'detail'" class="animate-pulse space-y-6 p-6">
    <div>
      <div class="h-3 bg-slate-700/30 rounded w-16 mb-2" />
      <div class="h-5 bg-slate-700/50 rounded w-2/3" />
    </div>
    <div>
      <div class="h-3 bg-slate-700/30 rounded w-16 mb-2" />
      <div class="flex gap-2">
        <div class="h-8 bg-slate-700/50 rounded w-16" />
        <div class="h-8 bg-slate-700/50 rounded w-16" />
        <div class="h-8 bg-slate-700/50 rounded w-16" />
        <div class="h-8 bg-slate-700/50 rounded w-16" />
      </div>
    </div>
    <div>
      <div class="h-3 bg-slate-700/30 rounded w-16 mb-2" />
      <div class="h-20 bg-slate-700/50 rounded w-full" />
    </div>
  </div>

  <!-- Text skeleton -->
  <div v-else class="animate-pulse space-y-2 p-4">
    <div v-for="i in count" :key="i" class="h-3.5 bg-slate-700/50 rounded" :class="i === count ? 'w-2/3' : 'w-full'" />
  </div>
</template>
