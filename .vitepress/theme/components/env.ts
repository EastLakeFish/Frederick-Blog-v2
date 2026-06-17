import { computed } from 'vue';

export const domainsAvailable = [
    "frederickyang.com",
    "eastlakefish.com",
]

export const currentDomain = computed(() => {
  if (typeof window === 'undefined') return '[window undefined]';
  const hostname = location.hostname.split('.').slice(-2).join('.')
  if (domainsAvailable.includes(hostname)) return hostname
  return "[under development]"
})
