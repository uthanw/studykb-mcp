<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  fetchMaterialIndex,
  fetchMaterialContent,
  type ParsedIndex,
  type IndexChapter,
} from '../../api'
import AppSkeleton from '../ui/AppSkeleton.vue'
import MarkdownViewer from '../MarkdownViewer.vue'

const props = defineProps<{
  category: string
  material: string
}>()

const emit = defineEmits<{
  close: []
}>()

const loading = ref(true)
const indexData = ref<ParsedIndex | null>(null)
const rawContent = ref<string | null>(null)
const isRawFormat = ref(false)

const expandedNodes = ref<Set<string>>(new Set())
const previewContent = ref<string | null>(null)
const previewLoading = ref(false)
const previewRange = ref<{ start: number; end: number } | null>(null)
const searchQuery = ref('')

onMounted(async () => {
  try {
    const result = await fetchMaterialIndex(props.category, props.material)
    if (result.format === 'csv' && result.parsed) {
      indexData.value = result.parsed
      // Auto-expand top-level chapters
      for (const ch of result.parsed.chapters) {
        if (ch.depth === 0) {
          expandedNodes.value.add(ch.number || `${ch.start}-${ch.end}`)
        }
      }
    } else if (result.content) {
      rawContent.value = result.content
      isRawFormat.value = true
    }
  } catch (e) {
    console.error('Failed to load index:', e)
  } finally {
    loading.value = false
  }
})

// Build tree from flat chapters
interface TreeNode extends IndexChapter {
  children: TreeNode[]
  id: string
}

const tree = computed<TreeNode[]>(() => {
  if (!indexData.value) return []

  const chapters = indexData.value.chapters
  const root: TreeNode[] = []
  const stack: TreeNode[] = []

  for (const ch of chapters) {
    const node: TreeNode = {
      ...ch,
      children: [],
      id: ch.number || `${ch.start}-${ch.end}`,
    }

    while (stack.length > 0 && stack[stack.length - 1].depth >= ch.depth) {
      stack.pop()
    }

    if (stack.length === 0) {
      root.push(node)
    } else {
      stack[stack.length - 1].children.push(node)
    }

    stack.push(node)
  }

  return root
})

// Filter tree by search query
const filteredTree = computed<TreeNode[]>(() => {
  if (!searchQuery.value.trim()) return tree.value

  const q = searchQuery.value.toLowerCase()

  function matchNode(node: TreeNode): TreeNode | null {
    const titleMatch = node.title.toLowerCase().includes(q)
    const tagsMatch = node.tags?.toLowerCase().includes(q)
    const numberMatch = node.number?.toLowerCase().includes(q)

    const filteredChildren = node.children
      .map(c => matchNode(c))
      .filter((c): c is TreeNode => c !== null)

    if (titleMatch || tagsMatch || numberMatch || filteredChildren.length > 0) {
      return { ...node, children: filteredChildren }
    }
    return null
  }

  return tree.value
    .map(n => matchNode(n))
    .filter((n): n is TreeNode => n !== null)
})

// Filter lookups by search
const filteredLookups = computed(() => {
  if (!indexData.value?.lookups) return []
  if (!searchQuery.value.trim()) return indexData.value.lookups

  const q = searchQuery.value.toLowerCase()
  return indexData.value.lookups.filter(
    lk => lk.keywords.toLowerCase().includes(q) || lk.title.toLowerCase().includes(q)
  )
})

function toggleExpand(id: string) {
  const next = new Set(expandedNodes.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedNodes.value = next
}

function isExpanded(id: string) {
  return expandedNodes.value.has(id)
}

async function previewSection(start: number, end: number) {
  previewRange.value = { start, end }
  previewLoading.value = true
  try {
    const result = await fetchMaterialContent(
      props.category, props.material, start, end
    )
    previewContent.value = result.lines.map(l => l.text).join('\n')
  } catch (e) {
    previewContent.value = '加载失败'
  } finally {
    previewLoading.value = false
  }
}

function depthIndent(depth: number) {
  return { paddingLeft: `${depth * 16 + 8}px` }
}
</script>

<template>
  <div class="flex flex-col h-full max-h-[80vh]">
    <!-- Header -->
    <div class="flex items-center justify-between px-5 py-3 border-b border-slate-700 flex-shrink-0">
      <div class="flex items-center gap-2.5">
        <span class="text-green-400 text-lg">📑</span>
        <span class="text-sm font-semibold text-slate-200">章节索引</span>
        <span v-if="indexData?.meta" class="text-xs text-slate-500">
          {{ indexData.meta.source }} · {{ Number(indexData.meta.total_lines || 0).toLocaleString() }} 行
        </span>
      </div>
      <button
        class="p-1 text-slate-400 hover:text-slate-200 transition-colors rounded-lg hover:bg-slate-700/50"
        @click="emit('close')"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="p-5">
      <AppSkeleton type="list" :count="6" />
    </div>

    <!-- Raw MD fallback -->
    <div v-else-if="isRawFormat && rawContent" class="flex-1 overflow-y-auto p-5">
      <MarkdownViewer :content="rawContent" />
    </div>

    <!-- Structured CSV view -->
    <template v-else-if="indexData">
      <!-- Search bar -->
      <div class="px-4 py-2 border-b border-slate-700 flex-shrink-0">
        <div class="relative">
          <svg class="absolute left-2.5 top-2 w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索章节或知识点..."
            class="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-800 border border-slate-700 rounded-md text-slate-300 placeholder-slate-500 focus:border-sky-500 focus:outline-none"
          >
        </div>
      </div>

      <div class="flex flex-1 overflow-hidden">
        <!-- Left: tree -->
        <div class="w-1/2 overflow-y-auto border-r border-slate-700">
          <!-- Overview -->
          <div v-if="indexData.overview.length && !searchQuery" class="border-b border-slate-700/50">
            <div class="px-3 py-1.5 text-[10px] uppercase text-slate-500 font-medium tracking-wider">概览</div>
            <div
              v-for="item in indexData.overview"
              :key="`ov-${item.start}`"
              class="flex items-center justify-between px-3 py-1.5 text-xs hover:bg-slate-800/70 cursor-pointer transition-colors"
              @click="previewSection(item.start, item.end)"
            >
              <span class="text-slate-300 truncate">{{ item.title }}</span>
              <span class="text-slate-600 text-[10px] flex-shrink-0 ml-2">{{ item.start }}-{{ item.end }}</span>
            </div>
          </div>

          <!-- Chapter tree -->
          <div class="py-1">
            <template v-for="node in filteredTree" :key="node.id">
              <div
                class="flex items-center gap-1 py-1.5 pr-3 text-xs hover:bg-slate-800/70 cursor-pointer transition-colors group"
                :style="depthIndent(node.depth)"
                @click="previewSection(node.start, node.end)"
              >
                <!-- Expand toggle -->
                <button
                  v-if="node.children.length"
                  class="w-4 h-4 flex items-center justify-center text-slate-500 hover:text-slate-300 flex-shrink-0"
                  @click.stop="toggleExpand(node.id)"
                >
                  <svg
                    class="w-3 h-3 transition-transform"
                    :class="{ 'rotate-90': isExpanded(node.id) }"
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <span v-else class="w-4 flex-shrink-0" />

                <!-- Number -->
                <span v-if="node.number" class="text-sky-400/80 flex-shrink-0 font-mono">{{ node.number }}</span>

                <!-- Title -->
                <span class="text-slate-300 truncate">{{ node.title }}</span>

                <!-- Line range -->
                <span class="text-slate-600 text-[10px] ml-auto flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  {{ node.start }}-{{ node.end }}
                </span>
              </div>

              <!-- Children (recursive) -->
              <template v-if="isExpanded(node.id)">
                <template v-for="child in node.children" :key="child.id">
                  <div
                    class="flex items-center gap-1 py-1.5 pr-3 text-xs hover:bg-slate-800/70 cursor-pointer transition-colors group"
                    :style="depthIndent(child.depth)"
                    @click="previewSection(child.start, child.end)"
                  >
                    <button
                      v-if="child.children.length"
                      class="w-4 h-4 flex items-center justify-center text-slate-500 hover:text-slate-300 flex-shrink-0"
                      @click.stop="toggleExpand(child.id)"
                    >
                      <svg
                        class="w-3 h-3 transition-transform"
                        :class="{ 'rotate-90': isExpanded(child.id) }"
                        fill="none" stroke="currentColor" viewBox="0 0 24 24"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                    <span v-else class="w-4 flex-shrink-0" />

                    <span v-if="child.number" class="text-sky-400/60 flex-shrink-0 font-mono text-[11px]">{{ child.number }}</span>
                    <span class="text-slate-400 truncate">{{ child.title }}</span>
                    <span class="text-slate-600 text-[10px] ml-auto flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                      {{ child.start }}-{{ child.end }}
                    </span>
                  </div>

                  <!-- Level 3 children -->
                  <template v-if="isExpanded(child.id)">
                    <div
                      v-for="sub in child.children"
                      :key="sub.id"
                      class="flex items-center gap-1 py-1 pr-3 text-xs hover:bg-slate-800/70 cursor-pointer transition-colors group"
                      :style="depthIndent(sub.depth)"
                      @click="previewSection(sub.start, sub.end)"
                    >
                      <span class="w-4 flex-shrink-0" />
                      <span v-if="sub.number" class="text-sky-400/40 flex-shrink-0 font-mono text-[10px]">{{ sub.number }}</span>
                      <span class="text-slate-500 truncate">{{ sub.title }}</span>
                      <span class="text-slate-600 text-[10px] ml-auto flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                        {{ sub.start }}-{{ sub.end }}
                      </span>
                    </div>
                  </template>
                </template>
              </template>
            </template>
          </div>
        </div>

        <!-- Right: preview -->
        <div class="w-1/2 overflow-y-auto flex flex-col">
          <div v-if="previewLoading" class="p-4">
            <AppSkeleton type="text" :count="5" />
          </div>
          <div v-else-if="!previewContent" class="flex-1 flex items-center justify-center text-slate-500 text-sm">
            <div class="text-center">
              <svg class="w-8 h-8 mx-auto mb-2 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <p>点击左侧章节预览内容</p>
            </div>
          </div>
          <template v-else>
            <div class="px-3 py-2 border-b border-slate-700 flex items-center gap-2 text-xs text-slate-500 flex-shrink-0">
              <span>行 {{ previewRange?.start }}-{{ previewRange?.end }}</span>
            </div>
            <div class="flex-1 overflow-y-auto p-3">
              <MarkdownViewer :content="previewContent" />
            </div>
          </template>
        </div>
      </div>

      <!-- Lookup tags -->
      <div v-if="filteredLookups.length" class="border-t border-slate-700 px-4 py-2 flex-shrink-0">
        <div class="flex items-center gap-1.5 mb-1.5">
          <span class="text-[10px] uppercase text-slate-500 font-medium tracking-wider">快速查找</span>
        </div>
        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="lk in filteredLookups"
            :key="`lk-${lk.start}`"
            class="text-[11px] px-2 py-0.5 bg-sky-500/10 text-sky-400 rounded-full cursor-pointer hover:bg-sky-500/20 transition-colors"
            :title="`${lk.section ? lk.section + ' · ' : ''}行 ${lk.start}-${lk.end}`"
            @click="previewSection(lk.start, lk.end)"
          >
            {{ lk.title || lk.keywords.split(';')[0] }}
          </span>
        </div>
      </div>
    </template>

    <!-- No index -->
    <div v-else class="flex-1 flex items-center justify-center text-slate-500 text-sm p-5">
      暂无索引数据
    </div>
  </div>
</template>
