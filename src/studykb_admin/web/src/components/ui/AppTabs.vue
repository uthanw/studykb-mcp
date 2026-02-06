<script setup lang="ts">
defineProps<{
  items: { key: string; label: string }[]
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [key: string]
}>()
</script>

<template>
  <div class="flex border-b border-slate-700">
    <button
      v-for="item in items"
      :key="item.key"
      class="px-5 py-2.5 text-sm transition-colors relative"
      :class="modelValue === item.key ? 'text-sky-400' : 'text-slate-400 hover:text-slate-300'"
      @click="emit('update:modelValue', item.key)"
    >
      {{ item.label }}
      <span
        v-if="modelValue === item.key"
        class="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-400"
      ></span>
    </button>
  </div>
</template>
