<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchCategories, type Category } from '@/api'

const router = useRouter()
const categories = ref<Category[]>([])
const loading = ref(true)

async function loadCategories() {
  loading.value = true
  try {
    categories.value = await fetchCategories()
  } finally {
    loading.value = false
  }
}

function goToProgress(name: string) {
  router.push(`/progress/${name}`)
}

onMounted(loadCategories)
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header -->
    <header class="px-6 py-4 border-b border-slate-700">
      <h1 class="text-xl font-semibold text-slate-100">进度管理</h1>
      <p class="text-sm text-slate-400 mt-1">查看和管理学习进度</p>
    </header>

    <!-- Content -->
    <div class="flex-1 p-6 overflow-auto">
      <div v-if="loading" class="flex items-center justify-center h-64">
        <div class="animate-spin w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full"></div>
      </div>

      <div v-else-if="categories.length === 0" class="flex flex-col items-center justify-center h-64 text-slate-400">
        <svg class="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p class="text-lg">暂无分类</p>
        <p class="text-sm mt-1">请先创建分类并初始化进度</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="category in categories"
          :key="category.name"
          class="bg-slate-800 rounded-lg p-4 border border-slate-700 hover:border-slate-600 transition-colors cursor-pointer"
          @click="goToProgress(category.name)"
        >
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 bg-amber-600/20 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h3 class="font-medium text-slate-100">{{ category.name }}</h3>
              <p class="text-sm text-slate-400">{{ category.file_count }} 个资料</p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
            <span class="text-sm text-slate-400">点击查看进度详情</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
