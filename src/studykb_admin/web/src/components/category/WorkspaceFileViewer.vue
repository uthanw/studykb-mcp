<script setup lang="ts">
import { watch } from 'vue'
import { useWorkspaceStore } from '../../stores/useWorkspaceStore'
import MarkdownViewer from '../MarkdownViewer.vue'
import DiffViewer from '../DiffViewer.vue'
import FileHistoryPanel from '../FileHistoryPanel.vue'
import AppSkeleton from '../ui/AppSkeleton.vue'
import AppEmptyState from '../ui/AppEmptyState.vue'

const workspace = useWorkspaceStore()

const props = defineProps<{
  categoryName: string
  progressId: string
}>()

// Auto-load history when panel opens
watch(() => workspace.historyPanelOpen, (open) => {
  if (open && workspace.selectedFile) {
    workspace.loadHistory(props.categoryName, props.progressId)
  }
})
</script>

<template>
  <div class="flex-1 flex overflow-hidden">
    <!-- File List -->
    <div class="w-48 flex-shrink-0 border-r border-slate-700 overflow-y-auto">
      <!-- Header -->
      <div class="p-2.5 border-b border-slate-700 flex justify-between items-center">
        <span class="text-xs text-slate-500 font-medium">文件列表</span>
        <button
          class="p-1 text-slate-400 hover:text-slate-200 transition-colors"
          title="刷新"
          :disabled="workspace.loading"
          @click="workspace.refresh(categoryName, progressId)"
        >
          <svg class="w-4 h-4" :class="{ 'animate-spin': workspace.loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      <!-- Loading -->
      <AppSkeleton v-if="workspace.loading && workspace.files.length === 0" type="list" :count="3" />

      <!-- Empty -->
      <div v-else-if="workspace.files.length === 0" class="p-4">
        <AppEmptyState icon="file" title="暂无文件" />
      </div>

      <!-- File items -->
      <div v-else class="py-1">
        <div
          v-for="file in workspace.files"
          :key="file.path"
          class="group px-3 py-2 cursor-pointer transition-all flex items-center justify-between"
          :class="workspace.selectedFile === file.path ? 'bg-sky-600/20 text-sky-400' : 'text-slate-300 hover:bg-slate-800/70'"
          @click="workspace.selectFile(categoryName, progressId, file.path)"
        >
          <div class="flex items-center gap-2 min-w-0 flex-1">
            <span>{{ workspace.getFileIcon(file.path) }}</span>
            <span class="truncate text-sm">{{ file.path }}</span>
          </div>
          <button
            class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-1 flex-shrink-0 transition-opacity"
            title="删除文件"
            @click.stop="workspace.deleteFile(categoryName, progressId, file.path)"
          >
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Content Area -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Content toolbar (only when file selected) -->
      <div v-if="workspace.selectedFile" class="px-4 py-2 border-b border-slate-700 flex items-center justify-between bg-slate-800/40">
        <div class="flex items-center gap-3">
          <span class="text-sm text-slate-300 font-medium">{{ workspace.selectedFile }}</span>
          <!-- Close diff button -->
          <button
            v-if="workspace.diffMode"
            class="px-2 py-0.5 text-xs rounded bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors"
            @click="workspace.closeDiff()"
          >
            关闭对比
          </button>
        </div>
        <div class="flex items-center gap-2">
          <!-- History toggle -->
          <button
            class="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded transition-colors"
            :class="workspace.historyPanelOpen ? 'bg-sky-600/20 text-sky-400' : 'bg-slate-700 text-slate-400 hover:text-slate-200'"
            @click="workspace.toggleHistoryPanel()"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            历史
            <span v-if="workspace.historyVersions.length > 0" class="bg-slate-600 rounded-full px-1.5 py-0 text-xs min-w-[18px] text-center">
              {{ workspace.historyVersions.length }}
            </span>
          </button>
        </div>
      </div>

      <!-- Main content -->
      <div class="flex-1 flex overflow-hidden">
        <!-- File content / Diff viewer -->
        <div class="flex-1 overflow-y-auto">
          <!-- Loading -->
          <AppSkeleton v-if="workspace.loading" type="text" :count="8" />

          <!-- No file selected -->
          <div v-else-if="!workspace.selectedFile" class="h-full flex items-center justify-center">
            <AppEmptyState icon="file" title="选择一个文件查看内容" />
          </div>

          <!-- Diff mode -->
          <div v-else-if="workspace.diffMode" class="h-full p-3">
            <DiffViewer
              :old-content="workspace.diffOldContent"
              :new-content="workspace.diffNewContent"
              :old-label="workspace.diffOldLabel"
              :new-label="workspace.diffNewLabel"
              :view-type="workspace.diffViewType"
              @update:view-type="workspace.diffViewType = $event"
            />
          </div>

          <!-- Markdown -->
          <div v-else-if="workspace.isMarkdownFile(workspace.selectedFile)" class="p-5">
            <MarkdownViewer :content="workspace.fileContent" />
          </div>

          <!-- Plain text -->
          <div v-else class="p-5">
            <pre class="text-sm text-slate-300 whitespace-pre-wrap font-mono bg-slate-800 rounded-lg p-4 overflow-x-auto">{{ workspace.fileContent }}</pre>
          </div>
        </div>

        <!-- History panel (right side, collapsible) -->
        <div
          v-if="workspace.historyPanelOpen && workspace.selectedFile"
          class="w-72 flex-shrink-0 border-l border-slate-700 bg-slate-850 overflow-hidden"
        >
          <FileHistoryPanel
            :versions="workspace.historyVersions"
            :loading="workspace.historyLoading"
            @view="workspace.viewVersion(categoryName, progressId, $event)"
            @rollback="workspace.rollbackToVersion(categoryName, progressId, $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>
