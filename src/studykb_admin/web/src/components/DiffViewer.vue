<script setup lang="ts">
import { computed } from 'vue'
import { diffLines, type Change } from 'diff'

const props = withDefaults(
  defineProps<{
    oldContent: string
    newContent: string
    oldLabel?: string
    newLabel?: string
    viewType?: 'unified' | 'split'
  }>(),
  {
    oldLabel: '旧版本',
    newLabel: '新版本',
    viewType: 'unified',
  }
)

const emit = defineEmits<{
  (e: 'update:viewType', value: 'unified' | 'split'): void
}>()

// Compute diff changes
const changes = computed<Change[]>(() => {
  return diffLines(props.oldContent, props.newContent)
})

// Statistics
const stats = computed(() => {
  let added = 0
  let removed = 0
  for (const c of changes.value) {
    const lineCount = c.value.endsWith('\n') ? c.value.split('\n').length - 1 : c.value.split('\n').length
    if (c.added) added += lineCount
    else if (c.removed) removed += lineCount
  }
  return { added, removed }
})

// ── Unified view lines ──────────────────────────────────

interface UnifiedLine {
  type: 'added' | 'removed' | 'unchanged'
  oldNum: number | null
  newNum: number | null
  text: string
}

const unifiedLines = computed<UnifiedLine[]>(() => {
  const lines: UnifiedLine[] = []
  let oldNum = 1
  let newNum = 1

  for (const change of changes.value) {
    const raw = change.value
    const textLines = raw.endsWith('\n')
      ? raw.slice(0, -1).split('\n')
      : raw.split('\n')

    for (const text of textLines) {
      if (change.added) {
        lines.push({ type: 'added', oldNum: null, newNum, text })
        newNum++
      } else if (change.removed) {
        lines.push({ type: 'removed', oldNum, newNum: null, text })
        oldNum++
      } else {
        lines.push({ type: 'unchanged', oldNum, newNum, text })
        oldNum++
        newNum++
      }
    }
  }
  return lines
})

// ── Split view lines ────────────────────────────────────

interface SplitRow {
  left: { num: number | null; text: string; type: 'removed' | 'unchanged' | 'empty' }
  right: { num: number | null; text: string; type: 'added' | 'unchanged' | 'empty' }
}

const splitRows = computed<SplitRow[]>(() => {
  const rows: SplitRow[] = []
  let oldNum = 1
  let newNum = 1

  // Process changes, grouping adjacent removed+added as pairs
  let i = 0
  const ch = changes.value
  while (i < ch.length) {
    const change = ch[i]

    if (!change.added && !change.removed) {
      // Context lines — both sides
      const textLines = change.value.endsWith('\n')
        ? change.value.slice(0, -1).split('\n')
        : change.value.split('\n')
      for (const text of textLines) {
        rows.push({
          left: { num: oldNum, text, type: 'unchanged' },
          right: { num: newNum, text, type: 'unchanged' },
        })
        oldNum++
        newNum++
      }
      i++
    } else if (change.removed && i + 1 < ch.length && ch[i + 1].added) {
      // Removed + Added pair — show side by side
      const removedLines = change.value.endsWith('\n')
        ? change.value.slice(0, -1).split('\n')
        : change.value.split('\n')
      const addedLines = ch[i + 1].value.endsWith('\n')
        ? ch[i + 1].value.slice(0, -1).split('\n')
        : ch[i + 1].value.split('\n')

      const maxLen = Math.max(removedLines.length, addedLines.length)
      for (let j = 0; j < maxLen; j++) {
        rows.push({
          left: j < removedLines.length
            ? { num: oldNum++, text: removedLines[j], type: 'removed' }
            : { num: null, text: '', type: 'empty' },
          right: j < addedLines.length
            ? { num: newNum++, text: addedLines[j], type: 'added' }
            : { num: null, text: '', type: 'empty' },
        })
      }
      i += 2
    } else if (change.removed) {
      // Only removed
      const textLines = change.value.endsWith('\n')
        ? change.value.slice(0, -1).split('\n')
        : change.value.split('\n')
      for (const text of textLines) {
        rows.push({
          left: { num: oldNum++, text, type: 'removed' },
          right: { num: null, text: '', type: 'empty' },
        })
      }
      i++
    } else if (change.added) {
      // Only added
      const textLines = change.value.endsWith('\n')
        ? change.value.slice(0, -1).split('\n')
        : change.value.split('\n')
      for (const text of textLines) {
        rows.push({
          left: { num: null, text: '', type: 'empty' },
          right: { num: newNum++, text, type: 'added' },
        })
      }
      i++
    } else {
      i++
    }
  }

  return rows
})

function setViewType(type: 'unified' | 'split') {
  emit('update:viewType', type)
}
</script>

<template>
  <div class="flex flex-col h-full bg-slate-900 rounded-lg overflow-hidden border border-slate-700">
    <!-- Toolbar -->
    <div class="flex items-center justify-between px-4 py-2 bg-slate-800/80 border-b border-slate-700">
      <div class="flex items-center gap-4 text-xs">
        <span class="text-slate-400">{{ oldLabel }}</span>
        <span class="text-slate-600">→</span>
        <span class="text-slate-400">{{ newLabel }}</span>
      </div>
      <div class="flex items-center gap-3">
        <!-- Stats -->
        <span v-if="stats.added" class="text-xs text-emerald-400 font-mono">+{{ stats.added }}</span>
        <span v-if="stats.removed" class="text-xs text-red-400 font-mono">-{{ stats.removed }}</span>
        <!-- View toggle -->
        <div class="flex rounded-md overflow-hidden border border-slate-600">
          <button
            class="px-2.5 py-1 text-xs transition-colors"
            :class="viewType === 'unified' ? 'bg-sky-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-slate-200'"
            @click="setViewType('unified')"
          >
            统一
          </button>
          <button
            class="px-2.5 py-1 text-xs transition-colors"
            :class="viewType === 'split' ? 'bg-sky-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-slate-200'"
            @click="setViewType('split')"
          >
            并排
          </button>
        </div>
      </div>
    </div>

    <!-- No changes -->
    <div v-if="stats.added === 0 && stats.removed === 0" class="flex-1 flex items-center justify-center text-slate-500 text-sm">
      两个版本内容完全相同
    </div>

    <!-- Unified view -->
    <div v-else-if="viewType === 'unified'" class="flex-1 overflow-auto">
      <table class="w-full text-xs font-mono border-collapse">
        <tbody>
          <tr
            v-for="(line, idx) in unifiedLines"
            :key="idx"
            :class="{
              'bg-red-950/40': line.type === 'removed',
              'bg-emerald-950/40': line.type === 'added',
            }"
          >
            <!-- Old line number -->
            <td class="w-12 text-right pr-2 select-none text-slate-600 border-r border-slate-800 sticky left-0 bg-inherit">
              {{ line.oldNum ?? '' }}
            </td>
            <!-- New line number -->
            <td class="w-12 text-right pr-2 select-none text-slate-600 border-r border-slate-800 bg-inherit">
              {{ line.newNum ?? '' }}
            </td>
            <!-- Symbol -->
            <td
              class="w-6 text-center select-none font-bold"
              :class="{
                'text-red-400': line.type === 'removed',
                'text-emerald-400': line.type === 'added',
              }"
            >
              {{ line.type === 'removed' ? '-' : line.type === 'added' ? '+' : ' ' }}
            </td>
            <!-- Content -->
            <td class="pl-2 pr-4 whitespace-pre-wrap break-all text-slate-300">{{ line.text }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Split view -->
    <div v-else class="flex-1 overflow-auto">
      <div class="flex min-h-full">
        <!-- Left (old) -->
        <div class="flex-1 border-r border-slate-700">
          <table class="w-full text-xs font-mono border-collapse">
            <tbody>
              <tr
                v-for="(row, idx) in splitRows"
                :key="'l' + idx"
                :class="{
                  'bg-red-950/40': row.left.type === 'removed',
                  'bg-slate-900/30': row.left.type === 'empty',
                }"
              >
                <td class="w-10 text-right pr-2 select-none text-slate-600 border-r border-slate-800 sticky left-0 bg-inherit">
                  {{ row.left.num ?? '' }}
                </td>
                <td
                  class="w-5 text-center select-none font-bold"
                  :class="{ 'text-red-400': row.left.type === 'removed' }"
                >
                  {{ row.left.type === 'removed' ? '-' : '' }}
                </td>
                <td class="pl-2 pr-3 whitespace-pre-wrap break-all text-slate-300">{{ row.left.text }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- Right (new) -->
        <div class="flex-1">
          <table class="w-full text-xs font-mono border-collapse">
            <tbody>
              <tr
                v-for="(row, idx) in splitRows"
                :key="'r' + idx"
                :class="{
                  'bg-emerald-950/40': row.right.type === 'added',
                  'bg-slate-900/30': row.right.type === 'empty',
                }"
              >
                <td class="w-10 text-right pr-2 select-none text-slate-600 border-r border-slate-800 sticky left-0 bg-inherit">
                  {{ row.right.num ?? '' }}
                </td>
                <td
                  class="w-5 text-center select-none font-bold"
                  :class="{ 'text-emerald-400': row.right.type === 'added' }"
                >
                  {{ row.right.type === 'added' ? '+' : '' }}
                </td>
                <td class="pl-2 pr-3 whitespace-pre-wrap break-all text-slate-300">{{ row.right.text }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
