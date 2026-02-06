<script setup lang="ts">
import { ref } from 'vue'
import { useCategoryStore } from '../../stores/useCategoryStore'
import AppModal from '../ui/AppModal.vue'

const store = useCategoryStore()

const visible = defineModel<boolean>('visible', { required: true })
const newCategoryName = ref('')

async function handleCreate() {
  if (!newCategoryName.value.trim()) return
  try {
    await store.create(newCategoryName.value.trim())
    newCategoryName.value = ''
    visible.value = false
  } catch {
    // Error already handled by store with toast
  }
}

function handleClose() {
  newCategoryName.value = ''
  visible.value = false
}
</script>

<template>
  <AppModal v-model:visible="visible" title="新建分类" width="400px">
    <div class="p-6">
      <input
        v-model="newCategoryName"
        type="text"
        class="w-full px-3 py-2.5 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-sky-500 transition-colors placeholder-slate-500"
        placeholder="输入分类名称"
        autofocus
        @keyup.enter="handleCreate"
      />
      <div class="flex justify-end gap-3 mt-5">
        <button
          class="px-4 py-2 text-sm text-slate-400 hover:text-slate-300 rounded-lg hover:bg-slate-700/50 transition-colors"
          @click="handleClose"
        >
          取消
        </button>
        <button
          class="px-4 py-2 text-sm bg-sky-500 text-white rounded-lg hover:bg-sky-600 disabled:opacity-50 transition-colors"
          :disabled="!newCategoryName.trim()"
          @click="handleCreate"
        >
          创建
        </button>
      </div>
    </div>
  </AppModal>
</template>
