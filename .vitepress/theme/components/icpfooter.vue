<!-- .vitepress/theme/icpfooter.vue -->
<script setup>
import DefaultTheme from 'vitepress/theme'
import IcpFooter from './icp.vue'

const { Layout } = DefaultTheme
</script>

<template>
  <Layout>
    <template #layout-bottom>
      <IcpFooter />
    </template>
  </Layout>
</template>