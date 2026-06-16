import { defineConfig } from 'vitepress'
import { fileURLToPath, URL } from 'node:url'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "EastLakeFish",
  description: "A personal blog where I release latest updates.",

  vite: {
    resolve: {
      alias: {
        '/docs': fileURLToPath(new URL('../', import.meta.url))
      }
    }
  },

  head: [
    ['link', { rel: 'icon', href: '/favicon.svg', type: 'image/svg+xml' }]
  ],

  markdown: {
    math: true,
  },

  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config

    footer: {
      message: '<a href="https://beian.miit.gov.cn" target="_blank">鄂ICP备2024070719号-1</a>',
      copyright: '©2026 All rights reserved.',
    },

    nav: [
      { text: 'Home', link: '/' },
      { text: 'About', link: '/meet-me' },
      { text: 'Navigate', link: '/contents' },
      { text: 'License', link: '/license' },
      { text: 'Source Files', link: '/sourceindex' },
    ],

    sidebar: [
      {
        text: 'About',
        link: '/meet-me',
      },
      {
        text: 'Navigate',
        link: '/contents',
      },
      {
        text: 'License',
        link: '/license',
      },
      {
        text: 'Source Files',
        link: '/sourceindex',
      },
      {
        text: 'Notes',
        items: [
          { 
            text: 'Machine Learning',
            items: [
              { text: 'Sharding ImageNet', link: '/notes/machine-learning/sharding-imagenet' },
              { text: 'Efficient ImageNet', link: '/notes/machine-learning/efficient-imagenet' },
              { text: 'Parallel Training', link: '/notes/machine-learning/parallel-training' },
            ],
            link: "/notes/machine-learning/index",
          },
        ]
      },
      {
        text: 'Life',
        items: [
          { text: 'Photography', link: '/toc/photography' },
        ]
      },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/EastLakeFish' }
    ],

    search: {
      provider: 'local',
    }
  }
})
