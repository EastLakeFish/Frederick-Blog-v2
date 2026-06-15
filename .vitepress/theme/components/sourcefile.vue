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

watchEffect(async () => {
  if (!visibleSource.value) {
    html.value = ''
    return
  }

  html.value = await codeToHtml(visibleSource.value, {
    lang: props.lang,
    theme: isDark.value ? 'github-dark' : 'github-light'
  })
})
</script>

<template>
  <div v-if="resolvedSource" class="source-file">
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