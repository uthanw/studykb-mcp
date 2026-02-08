<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import katex from 'katex'

const props = defineProps<{
  content: string
}>()

const container = ref<HTMLElement | null>(null)

// KaTeX: pre-process LaTeX before marked parses it
// Replace $$ ... $$ (display) and $ ... $ (inline) with rendered HTML
function renderLatex(text: string): string {
  // Display math: $$ ... $$ (possibly multiline)
  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, tex) => {
    try {
      return katex.renderToString(tex.trim(), { displayMode: true, throwOnError: false })
    } catch {
      return `<span class="katex-error">${tex}</span>`
    }
  })

  // Inline math: $ ... $ (but not $$ and not inside code)
  // Negative lookbehind for \ and $, negative lookahead for $
  text = text.replace(/(?<!\$)\$(?!\$)((?:[^$\\]|\\.)+?)\$(?!\$)/g, (_, tex) => {
    try {
      return katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false })
    } catch {
      return `<span class="katex-error">${tex}</span>`
    }
  })

  return text
}

// Configure marked with custom renderer for code highlighting
const renderer = new marked.Renderer()
renderer.code = function({ text, lang }: { text: string; lang?: string }) {
  const language = lang || ''
  let highlighted: string
  if (language && hljs.getLanguage(language)) {
    try {
      highlighted = hljs.highlight(text, { language }).value
    } catch {
      highlighted = hljs.highlightAuto(text).value
    }
  } else {
    highlighted = hljs.highlightAuto(text).value
  }
  return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
}

// Don't let marked escape LaTeX HTML output
const originalParagraph = renderer.paragraph.bind(renderer)
renderer.paragraph = function(token: any) {
  // If the paragraph contains KaTeX output, return it without further escaping
  if (typeof token === 'object' && token.text && token.text.includes('class="katex')) {
    return `<p>${token.text}</p>`
  }
  return originalParagraph(token)
}

marked.setOptions({
  renderer,
  breaks: true,
  gfm: true,
})

const renderedHtml = computed(() => {
  if (!props.content) return ''
  try {
    // First render LaTeX, then pass to marked
    const withLatex = renderLatex(props.content)
    return marked(withLatex) as string
  } catch (e) {
    console.error('Markdown render error:', e)
    return `<pre>${props.content}</pre>`
  }
})

// Re-highlight code blocks after render
function highlightCode() {
  if (container.value) {
    container.value.querySelectorAll('pre code').forEach((block) => {
      hljs.highlightElement(block as HTMLElement)
    })
  }
}

watch(renderedHtml, () => {
  setTimeout(highlightCode, 0)
})

onMounted(() => {
  setTimeout(highlightCode, 0)
})
</script>

<template>
  <div ref="container" class="markdown-viewer" v-html="renderedHtml"></div>
</template>

<style>
/* Import highlight.js dark theme */
@import 'highlight.js/styles/github-dark.css';
/* Import KaTeX styles */
@import 'katex/dist/katex.min.css';

.markdown-viewer {
  color: #e2e8f0;
  line-height: 1.7;
  font-size: 0.95rem;
}

.markdown-viewer h1,
.markdown-viewer h2,
.markdown-viewer h3,
.markdown-viewer h4,
.markdown-viewer h5,
.markdown-viewer h6 {
  color: #f1f5f9;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

.markdown-viewer h1 {
  font-size: 1.75rem;
  border-bottom: 1px solid #334155;
  padding-bottom: 0.3em;
}

.markdown-viewer h2 {
  font-size: 1.5rem;
  border-bottom: 1px solid #334155;
  padding-bottom: 0.3em;
}

.markdown-viewer h3 {
  font-size: 1.25rem;
}

.markdown-viewer h4 {
  font-size: 1.1rem;
}

.markdown-viewer p {
  margin-bottom: 1em;
}

.markdown-viewer a {
  color: #38bdf8;
  text-decoration: none;
}

.markdown-viewer a:hover {
  text-decoration: underline;
}

.markdown-viewer code {
  background-color: #1e293b;
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-family: 'Fira Code', 'JetBrains Mono', Consolas, monospace;
  font-size: 0.9em;
}

.markdown-viewer pre {
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 1em;
  overflow-x: auto;
  margin: 1em 0;
}

.markdown-viewer pre code {
  background-color: transparent;
  padding: 0;
  font-size: 0.85rem;
  line-height: 1.5;
}

.markdown-viewer ul,
.markdown-viewer ol {
  margin-bottom: 1em;
  padding-left: 2em;
}

.markdown-viewer li {
  margin-bottom: 0.25em;
}

.markdown-viewer blockquote {
  border-left: 4px solid #38bdf8;
  padding-left: 1em;
  margin: 1em 0;
  color: #94a3b8;
  font-style: italic;
}

.markdown-viewer table {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
}

.markdown-viewer th,
.markdown-viewer td {
  border: 1px solid #334155;
  padding: 0.5em 1em;
  text-align: left;
}

.markdown-viewer th {
  background-color: #1e293b;
  font-weight: 600;
}

.markdown-viewer tr:nth-child(even) {
  background-color: #1e293b40;
}

.markdown-viewer hr {
  border: none;
  border-top: 1px solid #334155;
  margin: 2em 0;
}

.markdown-viewer img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
}

/* Task list styles */
.markdown-viewer input[type="checkbox"] {
  margin-right: 0.5em;
}

/* KaTeX display math centering */
.markdown-viewer .katex-display {
  margin: 1em 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.markdown-viewer .katex-error {
  color: #f87171;
  font-family: monospace;
  font-size: 0.85em;
}
</style>
