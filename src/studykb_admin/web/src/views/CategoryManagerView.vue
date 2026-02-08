<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCategoryStore } from '../stores/useCategoryStore'
import { useProgressStore } from '../stores/useProgressStore'
import { useWorkspaceStore } from '../stores/useWorkspaceStore'
import { useTaskBridge } from '../composables/useTaskBridge'
import { useKeyboard } from '../composables/useKeyboard'
import McpConfigBox from '../components/McpConfigBox.vue'
import TaskProgressPanel from '../components/TaskProgressPanel.vue'
import CategorySidebar from '../components/category/CategorySidebar.vue'
import MaterialsToolbar from '../components/category/MaterialsToolbar.vue'
import MaterialsGrid from '../components/category/MaterialsGrid.vue'
import ProgressStatsHeader from '../components/category/ProgressStatsHeader.vue'
import ProgressEntryList from '../components/category/ProgressEntryList.vue'
import ProgressDetailPanel from '../components/category/ProgressDetailPanel.vue'
import NewCategoryModal from '../components/category/NewCategoryModal.vue'
import IndexTreeViewer from '../components/category/IndexTreeViewer.vue'
import AppModal from '../components/ui/AppModal.vue'

// Stores
const categoryStore = useCategoryStore()
const progressStore = useProgressStore()
const workspace = useWorkspaceStore()

// Router
const route = useRoute()
const router = useRouter()

// TaskBridge — replaces old getTaskCallbacks/getSessionId
const taskBridge = useTaskBridge()
const taskPanel = ref<InstanceType<typeof TaskProgressPanel> | null>(null)

onMounted(() => {
  // Register TaskBridge handlers
  taskBridge.on('connect', () => taskPanel.value?.connect())
  taskBridge.on('startTask', (name) => {
    if (name) taskPanel.value?.startTask(name)
  })
})

onUnmounted(() => {
  taskBridge.off('connect')
  taskBridge.off('startTask')
})

// Local UI state
const showNewCategoryModal = ref(false)
const mcpCollapsed = ref(true)
const taskPanelCollapsed = ref(true)

// Keyboard shortcuts
useKeyboard({
  onNewCategory: () => { showNewCategoryModal.value = true },
})

// Route-driven active tab
const activeTab = computed({
  get: () => (route.query.tab === 'progress' ? 'progress' : 'materials') as 'materials' | 'progress',
  set: (tab) => {
    router.replace({
      params: route.params,
      query: tab === 'materials' ? {} : { ...route.query, tab },
    })
  },
})

// Route-driven category name
const routeCategoryName = computed(() => {
  const name = route.params.name as string | undefined
  return name ? decodeURIComponent(name) : null
})

// Sync route → store on mount and route changes
watch(routeCategoryName, (name) => {
  if (name && name !== categoryStore.selectedCategoryName) {
    categoryStore.selectCategory(name)
  } else if (!name && categoryStore.selectedCategoryName) {
    // If route has no category but store has one, update route
    router.replace(`/categories/${encodeURIComponent(categoryStore.selectedCategoryName)}`)
  }
}, { immediate: true })

// Watch store category change → update route
watch(() => categoryStore.selectedCategoryName, (name) => {
  if (name) {
    const currentRouteName = route.params.name as string | undefined
    if (currentRouteName !== name) {
      router.replace({
        path: `/categories/${encodeURIComponent(name)}`,
        query: route.query,
      })
    }
  }
  // Reset dependent stores
  progressStore.reset()
  workspace.reset()
  if (activeTab.value === 'progress' && name) {
    progressStore.load(name)
  }
})

// Route-driven entry selection
const routeEntryId = computed(() => route.query.entry as string | undefined)

watch(routeEntryId, (entryId) => {
  if (entryId && progressStore.entries.length > 0) {
    const entry = progressStore.entries.find(e => e.id === entryId)
    if (entry && progressStore.selectedEntry?.id !== entryId) {
      progressStore.selectEntry(entry)
    }
  } else if (!entryId && progressStore.selectedEntry) {
    progressStore.selectedEntry = null
  }
})

// Watch entry selection → update route + load note
watch(() => progressStore.selectedEntry, (newEntry) => {
  const currentEntryId = route.query.entry
  if (newEntry) {
    if (currentEntryId !== newEntry.id) {
      router.replace({
        params: route.params,
        query: { ...route.query, entry: newEntry.id },
      })
    }
    workspace.reset()
    if (categoryStore.selectedCategoryName) {
      workspace.loadNote(categoryStore.selectedCategoryName, newEntry.id)
    }
  } else if (currentEntryId) {
    const { entry: _, ...rest } = route.query
    router.replace({ params: route.params, query: rest })
  }
})

// Tab switching
function handleTabChange(tab: 'materials' | 'progress') {
  activeTab.value = tab
  if (tab === 'progress' && categoryStore.selectedCategoryName) {
    progressStore.load(categoryStore.selectedCategoryName)
  }
}

// Upload handler
function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (!files || files.length === 0) return

  categoryStore.upload(files)
  target.value = ''
}

function handleDrop(event: DragEvent) {
  const files = event.dataTransfer?.files
  if (!files || files.length === 0) return
  categoryStore.upload(files)
}

function handleGenerateIndex() {
  categoryStore.genIndex(categoryStore.selectedMaterials)
}

function handleInitProgress() {
  categoryStore.initProgressAction()
}

// Category selection via sidebar
function handleCategorySelect(name: string) {
  router.push({
    path: `/categories/${encodeURIComponent(name)}`,
    query: {},
  })
}

// Task completion → reload data
function handleTaskComplete() {
  categoryStore.load()
  if (activeTab.value === 'progress' && categoryStore.selectedCategoryName) {
    progressStore.load(categoryStore.selectedCategoryName)
  }
}

onMounted(() => {
  categoryStore.load().then(() => {
    // After loading, if route has no category but store picked one, sync to route
    if (!routeCategoryName.value && categoryStore.selectedCategoryName) {
      router.replace(`/categories/${encodeURIComponent(categoryStore.selectedCategoryName)}`)
    }
    // If route has category, load progress if on progress tab
    if (activeTab.value === 'progress' && categoryStore.selectedCategoryName) {
      progressStore.load(categoryStore.selectedCategoryName).then(() => {
        // After loading entries, restore entry selection from route
        if (routeEntryId.value) {
          const entry = progressStore.entries.find(e => e.id === routeEntryId.value)
          if (entry) progressStore.selectEntry(entry)
        }
      })
    }
  })
})
</script>

<template>
  <div class="category-manager h-full flex flex-col">
    <!-- MCP Config Box -->
    <div class="flex-shrink-0 p-4 border-b border-slate-700">
      <McpConfigBox v-model:collapsed="mcpCollapsed" />
    </div>

    <!-- Main Content -->
    <div class="flex-1 flex min-h-0">
      <!-- Sidebar -->
      <CategorySidebar
        @new-category="showNewCategoryModal = true"
        @select="handleCategorySelect"
      />

      <!-- Main Panel -->
      <div class="flex-1 flex flex-col min-w-0">
        <!-- Tab Header -->
        <div class="flex-shrink-0 border-b border-slate-700">
          <div class="flex">
            <button
              class="px-6 py-3 text-sm font-medium transition-colors relative"
              :class="activeTab === 'materials' ? 'text-sky-400' : 'text-slate-400 hover:text-slate-300'"
              @click="handleTabChange('materials')"
            >
              资料管理
              <span
                v-if="activeTab === 'materials'"
                class="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-400"
              ></span>
            </button>
            <button
              class="px-6 py-3 text-sm font-medium transition-colors relative"
              :class="activeTab === 'progress' ? 'text-sky-400' : 'text-slate-400 hover:text-slate-300'"
              @click="handleTabChange('progress')"
            >
              进度管理
              <span
                v-if="activeTab === 'progress'"
                class="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-400"
              ></span>
            </button>
          </div>
        </div>

        <!-- Tab Content -->
          <!-- Materials Tab -->
          <div v-if="activeTab === 'materials'" class="flex-1 flex flex-col min-h-0">
            <MaterialsToolbar
              @upload="handleFileUpload"
              @generate-index="handleGenerateIndex"
              @init-progress="handleInitProgress"
            />
            <MaterialsGrid @drop="handleDrop" />
          </div>

          <!-- Progress Tab -->
          <div v-else class="flex-1 flex flex-col min-h-0">
            <ProgressStatsHeader :category-name="categoryStore.selectedCategoryName || ''" />
            <ProgressEntryList v-if="!progressStore.selectedEntry" class="flex-1 overflow-y-auto" :category-name="categoryStore.selectedCategoryName" />
            <ProgressDetailPanel v-else class="flex-1 min-h-0" :category-name="categoryStore.selectedCategoryName || ''" />
          </div>

        <!-- Task Progress Panel -->
        <div class="flex-shrink-0">
          <TaskProgressPanel
            ref="taskPanel"
            v-model:collapsed="taskPanelCollapsed"
            @task-complete="handleTaskComplete"
          />
        </div>
      </div>
    </div>

    <!-- New Category Modal -->
    <NewCategoryModal v-model:visible="showNewCategoryModal" />

    <!-- Index Preview Modal -->
    <AppModal
      :visible="!!categoryStore.indexPreview"
      title="章节索引"
      width="900px"
      @update:visible="categoryStore.closeIndexPreview()"
    >
      <IndexTreeViewer
        v-if="categoryStore.indexPreview"
        :category="categoryStore.indexPreview.category"
        :material="categoryStore.indexPreview.material"
        @close="categoryStore.closeIndexPreview()"
      />
    </AppModal>
  </div>
</template>

<style scoped>
.category-manager {
  background: rgb(15 23 42);
}
</style>
