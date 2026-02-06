<script setup lang="ts">
import { RouterView } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import AppToast from './components/ui/AppToast.vue'
import AppConfirmDialog from './components/ui/AppConfirmDialog.vue'
</script>

<template>
  <div class="flex h-screen bg-slate-900">
    <Sidebar />
    <main class="flex-1 overflow-auto">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
  </div>

  <!-- Global UI -->
  <AppToast />
  <AppConfirmDialog />
</template>
