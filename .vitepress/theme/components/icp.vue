<!-- .vitepress/theme/components/icp.vue -->
<script setup>
import { computed } from 'vue';

const ICP_CONFIG = {
  'frederickyang.com': '鄂ICP备2024070719号-1',
  'eastlakefish.com': '鄂ICP备2024070719号-2',
};

const currentDomain = computed(() => {
  if (typeof window === 'undefined') return '';
  return location.hostname.split('.').slice(-2).join('.');
});

const displayICP = computed(() => {
  return ICP_CONFIG[currentDomain.value] || null;
});

function getCopyright(domain) {
    const date = new Date()
    return "© " + date.getFullYear() + ", " + domain + ", all rights reserved."
}

const icpLink = 'https://beian.miit.gov.cn/';
</script>

<template>
  <ClientOnly>
    <footer class="site-footer">
      <a
        v-if="displayICP"
        :href="icpLink"
        target="_blank"
        rel="noopener noreferrer"
        class="icp-info"
      >
        ICP Filing No. {{ displayICP }}
        <span class="copyright">{{ getCopyright(currentDomain) }}</span>
      </a>
      <span v-else class="icp-placeholder">
        <i>under development</i>
        <span class="copyright">{{ getCopyright(Object.keys(ICP_CONFIG).join(', ')) }}</span>
      </span>
    </footer>
  </ClientOnly>
</template>

<style scoped>
.site-footer {
  padding: 20px 0;
  text-align: center;
  font-size: 14px;
  color: var(--vp-c-text-2);
  background-color: var(--vp-c-bg-soft);
  border-top: 1px solid var(--vp-c-divider);
}

.icp-info {
  color: var(--vp-c-text-2);
  text-decoration: none;
  transition: color 0.2s;
}

.icp-info:hover {
  color: var(--vp-c-text-1);
  text-decoration: underline;
}

.icp-placeholder {
  color: var(--vp-c-text-3);
}

.copyright {
  margin-left: 12px;
  color: var(--vp-c-text-3);
  font-size: 13px;
}
</style>