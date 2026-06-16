<script setup lang="ts">
import { computed } from 'vue'

const sources = import.meta.glob(
  '/docs/source/**/*.{py,ts,js,jsx,tsx,vue,css,scss,html,json,yml,yaml,toml,txt,sh,bash,c,cpp,h,hpp,java,rs,go,xml}',
  {
    query: '?raw',
    import: 'default',
    eager: true
  }
) as Record<string, string>

const files = computed(() => {
  return Object.keys(sources)
    .map((key) => key.replace(/^\/docs\/source\//, ''))
    .sort()
})

function fileIcon(file: string) {
  if (file.endsWith('/')) return '📁'
  return '📄'
}
</script>

<template>
  <section class="source-index">
    <div class="source-index-header">
      <h1>Source Files</h1>
      <p>
        <strong>Important:</strong>
        All our source files are licensed under GNU GPL 2.0 and are not authorized for academic use unless you cite this website.
        For more details, please refer to <a href="/license" target="_blank">license</a>.
      </p>
    </div>

    <div class="source-index-list">
      <a
        v-for="file in files"
        :key="file"
        class="source-index-entry"
        :href="`/docs/source/?file=${encodeURIComponent(file)}`"
      >
        <span class="source-index-icon">📄</span>
        <code>{{ file }}</code>
      </a>
    </div>
  </section>
</template>