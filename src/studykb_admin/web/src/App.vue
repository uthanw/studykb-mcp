<script setup lang="ts">
import { RouterView } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
</script>

<template>
  <div class="flex h-screen bg-slate-900">
    <Sidebar />
    <main class="flex-1 overflow-auto">
      <RouterView />
    </main>
  </div>
</template>
