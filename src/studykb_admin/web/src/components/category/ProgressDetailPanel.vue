<script setup lang="ts">
import { ref } from 'vue'
import { useProgressStore, statusOptions, getStatusColor } from '../../stores/useProgressStore'
import { useWorkspaceStore } from '../../stores/useWorkspaceStore'
import WorkspaceFileViewer from './WorkspaceFileViewer.vue'
import MarkdownViewer from '../MarkdownViewer.vue'
import AppEmptyState from '../ui/AppEmptyState.vue'
import AppSkeleton from '../ui/AppSkeleton.vue'

const progressStore = useProgressStore()
const workspace = useWorkspaceStore()

defineProps<{
  categoryName: string
}>()

const detailTab = ref<'info' | 'workspace'>('info')

function goBack() {
  progressStore.selectedEntry = null
  detailTab.value = 'info'
}
</script>

<template>
  <div class="flex-1 flex flex-col overflow-hidden min-h-0">
    <!-- No entry selected -->
    <div v-if="!progressStore.selectedEntry" class="flex-1 flex items-center justify-center">
      <AppEmptyState
        icon="chart"
        title="请选择一个进度条目"
        description="在左侧列表选择一个条目查看详情"
      />
    </div>

    <template v-else>
      <!-- Detail Header -->
      <div class="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
        <div class="flex items-center gap-3 min-w-0">
          <!-- Back button: visible on small detail area, always functional -->
          <button
            class="p-1 -ml-1 text-slate-400 hover:text-slate-200 transition-colors rounded-lg hover:bg-slate-700/50 flex-shrink-0"
            title="返回列表"
            @click="goBack"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h2 class="text-lg font-medium text-slate-100 truncate">{{ progressStore.selectedEntry.name }}</h2>
        </div>
        <div class="flex items-center gap-2 flex-shrink-0">
          <button
            v-if="!progressStore.editMode && detailTab === 'info'"
            class="px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors rounded-lg hover:bg-slate-700/50"
            @click="progressStore.startEdit()"
          >
            编辑
          </button>
          <button
            v-if="!progressStore.editMode && detailTab === 'info'"
            class="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 transition-colors rounded-lg hover:bg-red-500/10"
            @click="progressStore.deleteEntry(categoryName)"
          >
            删除
          </button>
          <template v-if="progressStore.editMode">
            <button
              class="px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors rounded-lg hover:bg-slate-700/50"
              @click="progressStore.editMode = false"
            >
              取消
            </button>
            <button
              class="px-4 py-1.5 text-sm bg-sky-600 hover:bg-sky-500 text-white rounded-lg transition-colors"
              @click="progressStore.saveEdit(categoryName)"
            >
              保存
            </button>
          </template>
        </div>
      </div>

      <!-- Detail Tabs -->
      <div class="flex border-b border-slate-700">
        <button
          class="px-5 py-2.5 text-sm transition-colors relative"
          :class="detailTab === 'info' ? 'text-sky-400' : 'text-slate-400 hover:text-slate-300'"
          @click="detailTab = 'info'"
        >
          基本信息
          <span
            v-if="detailTab === 'info'"
            class="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-400"
          ></span>
        </button>
        <button
          class="px-5 py-2.5 text-sm transition-colors relative"
          :class="detailTab === 'workspace' ? 'text-sky-400' : 'text-slate-400 hover:text-slate-300'"
          @click="detailTab = 'workspace'; workspace.loadFiles(categoryName, progressStore.selectedEntry!.id)"
        >
          工作区文件
          <span
            v-if="detailTab === 'workspace'"
            class="absolute bottom-0 left-0 right-0 h-0.5 bg-sky-400"
          ></span>
        </button>
      </div>

      <!-- Info Tab Content -->
      <div v-if="detailTab === 'info'" class="flex-1 overflow-y-auto p-6">
        <!-- View Mode -->
        <template v-if="!progressStore.editMode">
          <div class="space-y-6">
            <div>
              <label class="text-sm text-slate-400">ID</label>
              <p class="text-slate-200 font-mono text-sm mt-1">{{ progressStore.selectedEntry.id }}</p>
            </div>

            <div>
              <label class="text-sm text-slate-400">状态</label>
              <div class="flex items-center gap-2 mt-2">
                <button
                  v-for="opt in statusOptions"
                  :key="opt.value"
                  class="px-3 py-1.5 rounded-lg text-sm transition-colors"
                  :class="progressStore.selectedEntry!.status === opt.value
                    ? getStatusColor(opt.value) + ' ring-1 ring-current'
                    : 'text-slate-400 bg-slate-700/50 hover:bg-slate-700'"
                  @click="progressStore.quickStatusChange(categoryName, progressStore.selectedEntry!, opt.value)"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>

            <div v-if="progressStore.selectedEntry.comment">
              <label class="text-sm text-slate-400">备注</label>
              <p class="text-slate-200 mt-1 leading-relaxed">{{ progressStore.selectedEntry.comment }}</p>
            </div>

            <div v-if="progressStore.selectedEntry.related_sections.length > 0">
              <label class="text-sm text-slate-400">关联章节</label>
              <div class="mt-2 space-y-2">
                <div
                  v-for="(section, index) in progressStore.selectedEntry.related_sections"
                  :key="index"
                  class="px-3 py-2.5 bg-slate-800 rounded-lg text-sm"
                >
                  <span class="text-sky-400">{{ section.material }}</span>
                  <span class="text-slate-500">:</span>
                  <span class="text-slate-300">{{ section.start_line }}-{{ section.end_line }}</span>
                  <span v-if="section.desc" class="text-slate-400 ml-2">{{ section.desc }}</span>
                </div>
              </div>
            </div>

            <div v-if="progressStore.selectedEntry.updated_at">
              <label class="text-sm text-slate-400">更新时间</label>
              <p class="text-slate-200 mt-1">{{ new Date(progressStore.selectedEntry.updated_at).toLocaleString() }}</p>
            </div>

            <div v-if="progressStore.selectedEntry.review_count > 0">
              <label class="text-sm text-slate-400">复习次数</label>
              <p class="text-slate-200 mt-1">{{ progressStore.selectedEntry.review_count }}</p>
            </div>

            <!-- note.md inline preview -->
            <div v-if="workspace.noteLoading">
              <label class="text-sm text-slate-400">学习笔记</label>
              <AppSkeleton type="text" :count="4" />
            </div>
            <div v-else-if="workspace.noteContent">
              <label class="text-sm text-slate-400">学习笔记</label>
              <div class="mt-2 bg-slate-800/60 rounded-lg p-4 border border-slate-700/50">
                <MarkdownViewer :content="workspace.noteContent" />
              </div>
            </div>
          </div>
        </template>

        <!-- Edit Mode -->
        <template v-else>
          <div class="space-y-6">
            <div>
              <label class="text-sm text-slate-400">状态</label>
              <select
                v-model="progressStore.editData.status"
                class="mt-2 w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-sky-500 transition-colors"
              >
                <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>

            <div>
              <label class="text-sm text-slate-400">备注</label>
              <textarea
                v-model="progressStore.editData.comment"
                rows="4"
                class="mt-2 w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:border-sky-500 resize-none transition-colors"
                placeholder="添加备注..."
              />
            </div>
          </div>
        </template>
      </div>

      <!-- Workspace Tab Content -->
      <WorkspaceFileViewer
        v-else
        :category-name="categoryName"
        :progress-id="progressStore.selectedEntry.id"
      />
    </template>
  </div>
</template>
