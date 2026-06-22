<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import SourceFile from './sourcefile.vue'

const sources = import.meta.glob(
  '/docs/source/**/*.{py,ts,js,jsx,tsx,vue,css,scss,html,json,md,yml,yaml,toml,txt,sh,bash,c,cpp,h,hpp,java,rs,go,xml}',
  {
    query: '?raw',
    import: 'default',
    eager: true
  }
) as Record<string, string>

const urlFile = ref('')
const previousUrl = ref('')

onMounted(() => {
  urlFile.value = new URLSearchParams(window.location.search).get('file') ?? ''
  previousUrl.value = document.referrer || '/'
})

const normalizedFile = computed(() => {
  return urlFile.value
    .replace(/^\/+/, '')
    .replace(/^docs\/source\//, '')
    .replace(/^source\//, '')
})

const sourceKey = computed(() => {
  const suffix = `/source/${normalizedFile.value}`
  return Object.keys(sources).find((key) => key.endsWith(suffix)) ?? ''
})

const source = computed(() => {
  return sourceKey.value ? sources[sourceKey.value] : ''
})

const filename = computed(() => {
  return normalizedFile.value.split('/').pop() || normalizedFile.value
})

const downloadHref = computed(() => {
  return `/docs/source/${normalizedFile.value}`
})

const lang = computed(() => {
  const f = normalizedFile.value.toLowerCase()

  if (f.endsWith('.py')) return 'python'
  if (f.endsWith('.ts')) return 'typescript'
  if (f.endsWith('.tsx')) return 'tsx'
  if (f.endsWith('.js')) return 'javascript'
  if (f.endsWith('.jsx')) return 'jsx'
  if (f.endsWith('.vue')) return 'vue'
  if (f.endsWith('.css')) return 'css'
  if (f.endsWith('.scss')) return 'scss'
  if (f.endsWith('.html')) return 'html'
  if (f.endsWith('.json')) return 'json'
  if (f.endsWith('.md')) return 'markdown'
  if (f.endsWith('.yml') || f.endsWith('.yaml')) return 'yaml'
  if (f.endsWith('.toml')) return 'toml'
  if (f.endsWith('.sh') || f.endsWith('.bash')) return 'bash'
  if (f.endsWith('.c') || f.endsWith('.h')) return 'c'
  if (f.endsWith('.cpp') || f.endsWith('.hpp')) return 'cpp'
  if (f.endsWith('.java')) return 'java'
  if (f.endsWith('.rs')) return 'rust'
  if (f.endsWith('.go')) return 'go'
  if (f.endsWith('.xml')) return 'xml'

  return 'text'
})

function goBack() {
  if (window.history.length > 1) {
    window.history.back()
  } else {
    window.location.href = '/'
  }
}
</script>

<template>
  <section class="source-viewer">
    <div class="source-viewer-intro">
      <button class="source-viewer-back" type="button" @click="goBack">
        ← Back
      </button>

      <p v-if="source">
        You are previewing <code>{{ normalizedFile }}</code>.<br>
        Download it
        <a :href="downloadHref" :download="filename">here</a>.
        You can check out <a href="/license">license</a> here.
      </p>

      <p v-else>
        Source file not found: <code>{{ normalizedFile }}</code>
      </p>
    </div>

    <SourceFile
      v-if="source"
      :title="normalizedFile"
      :source="source"
      :lang="lang"
    />
    
    <div v-else class="source-file-missing">
      Could not find this file in <code>/docs/source/</code>.
    </div>

    <div class="source-viewer-intro">
      <button class="source-viewer-back" type="button" @click="goBack">
        ← Back
      </button>
    </div>

  </section>
</template>