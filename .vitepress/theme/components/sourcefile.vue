<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import { useData } from 'vitepress'
import { codeToHtml } from 'shiki'

const { isDark } = useData()

const props = withDefaults(defineProps<{
  title?: string
  source?: string
  file?: string
  lang?: string
  start?: number
  end?: number
}>(), {
  lang: undefined
})

const sources = import.meta.glob('/docs/source/**/*', {
  query: '?raw',
  import: 'default',
  eager: true
}) as Record<string, string>

const urlFile = ref('')

if (typeof window !== 'undefined') {
  urlFile.value = new URLSearchParams(window.location.search).get('file') ?? ''
}

const normalizedFile = computed(() => {
  const raw = props.file ?? urlFile.value
  return raw.replace(/^\/+/, '').replace(/^source\//, '')
})

const sourceKey = computed(() => {
  return `/docs/source/${normalizedFile.value}`
})

const resolvedSource = computed(() => {
  return props.source ?? sources[sourceKey.value] ?? ''
})

const resolvedTitle = computed(() => {
  return props.title ?? normalizedFile.value
})

const resolvedLang = computed(() => {
  if (props.lang) return props.lang

  const filename = resolvedTitle.value

  if (filename.endsWith('.py')) return 'python'
  if (filename.endsWith('.ts')) return 'typescript'
  if (filename.endsWith('.js')) return 'javascript'
  if (filename.endsWith('.vue')) return 'vue'
  if (filename.endsWith('.css')) return 'css'
  if (filename.endsWith('.json')) return 'json'
  if (filename.endsWith('.md')) return 'markdown'
  if (filename.endsWith('.html')) return 'html'
  if (filename.endsWith('.yml') || filename.endsWith('.yaml')) return 'yaml'

  return 'text'
})

const visibleSource = computed(() => {
  const lines = resolvedSource.value.split('\n')
  const start = props.start ?? 1
  const end = props.end ?? lines.length
  return lines.slice(start - 1, end).join('\n')
})

const html = ref('')
const isLoading = ref(false)

watchEffect(async () => {
  if (!visibleSource.value) {
    html.value = ''
    isLoading.value = false
    return
  }

  isLoading.value = true
  try {
    html.value = await codeToHtml(visibleSource.value, {
      lang: resolvedLang.value,
      theme: isDark.value ? 'github-dark' : 'github-light'
    })
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div v-if="resolvedSource && isLoading" class="source-file-loading">
    <div class="spinner"></div>
    <p>Parsing source file: <code>{{ resolvedTitle }}</code>...</p>
  </div>

  <div v-else-if="resolvedSource && !isLoading" class="source-file">
    <div class="source-file-header">
      <span class="source-file-title">{{ resolvedTitle }}</span>
      <span class="source-file-meta">{{ resolvedLang }}</span>
    </div>

    <div class="source-file-body" v-html="html" />
  </div>

  <div v-else class="source-file-missing">
    Source file not found: <code>{{ normalizedFile }}</code>
  </div>
</template>

<style scoped>
.source-file-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  
  margin: 1rem 0;
  padding: 3rem 1rem;
  
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-2);
}

.source-file-loading p {
  margin: 0;
  font-size: 0.95rem;
}

/* --- CSS Spinner Animation --- */
.spinner {
  width: 2.5rem;
  height: 2.5rem;
  border: 3px solid var(--vp-c-divider);
  border-top-color: var(--vp-c-brand-1);
  border-radius: 20%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>