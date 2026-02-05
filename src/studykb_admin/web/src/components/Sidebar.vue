<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/', name: '分类管理', icon: 'folder', exact: true },
  { path: '/settings', name: '设置', icon: 'settings', exact: true },
]

const isActive = (item: { path: string; exact: boolean }) => {
  if (item.exact) {
    return route.path === item.path
  }
  return route.path.startsWith(item.path)
}
</script>

<template>
  <aside class="w-16 bg-slate-800 border-r border-slate-700 flex flex-col items-center py-4">
    <!-- Logo -->
    <div class="mb-8">
      <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center text-white font-bold text-lg">
        K
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 flex flex-col gap-2">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-200"
        :class="isActive(item)
          ? 'bg-sky-500/20 text-sky-400'
          : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'"
        :title="item.name"
      >
        <!-- Folder icon -->
        <svg v-if="item.icon === 'folder'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
        <!-- Chart icon -->
        <svg v-else-if="item.icon === 'chart'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <!-- Settings icon -->
        <svg v-else-if="item.icon === 'settings'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </router-link>
    </nav>
  </aside>
</template>
