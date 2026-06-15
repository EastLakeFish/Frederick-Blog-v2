<script setup>
import { useData } from 'vitepress'

const { frontmatter } = useData()
</script>

<template>
  <div v-if="frontmatter.references">
    <h2>References</h2>

    <ul class="reference-list">
      <li
        v-for="(ref, key) in frontmatter.references"
        :key="key"
        :id="key"
      >
        {{ ref.authors }}.
        "{{ ref.title }}".
        <em>{{ ref.book }}</em>
        ({{ ref.year }}).
      </li>
    </ul>
  </div>
</template>