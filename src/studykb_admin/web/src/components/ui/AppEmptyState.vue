<script setup lang="ts">
withDefaults(defineProps<{
  icon?: 'folder' | 'file' | 'chart' | 'search'
  title: string
  description?: string
  actionText?: string
}>(), {
  icon: 'folder',
})

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-12 px-6 text-center">
    <!-- Icon -->
    <div class="w-16 h-16 mb-5 text-slate-600">
      <!-- Folder icon -->
      <svg v-if="icon === 'folder'" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 16C8 13.7909 9.79086 12 12 12H24L30 18H52C54.2091 18 56 19.7909 56 22V48C56 50.2091 54.2091 52 52 52H12C9.79086 52 8 50.2091 8 48V16Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <!-- File icon -->
      <svg v-else-if="icon === 'file'" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M38 8H16C13.7909 8 12 9.79086 12 12V52C12 54.2091 13.7909 56 16 56H48C50.2091 56 52 54.2091 52 52V22L38 8Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M38 8V22H52" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M24 34H40" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M24 42H36" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <!-- Chart icon -->
      <svg v-else-if="icon === 'chart'" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="36" width="10" height="20" rx="2" stroke="currentColor" stroke-width="2"/>
        <rect x="27" y="24" width="10" height="32" rx="2" stroke="currentColor" stroke-width="2"/>
        <rect x="44" y="12" width="10" height="44" rx="2" stroke="currentColor" stroke-width="2"/>
      </svg>
      <!-- Search icon -->
      <svg v-else viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="28" cy="28" r="16" stroke="currentColor" stroke-width="2"/>
        <path d="M40 40L54 54" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </div>

    <!-- Title -->
    <h3 class="text-base font-medium text-slate-400 mb-2">{{ title }}</h3>

    <!-- Description -->
    <p v-if="description" class="text-sm text-slate-500 max-w-sm leading-relaxed">
      {{ description }}
    </p>

    <!-- Action -->
    <button
      v-if="actionText"
      class="mt-5 px-4 py-2 text-sm bg-sky-500/20 text-sky-400 rounded-lg hover:bg-sky-500/30 transition-colors"
      @click="emit('action')"
    >
      {{ actionText }}
    </button>
  </div>
</template>
