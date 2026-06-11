import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Yang's Blog",
  description: "A personal blog where I release latest updates.",

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
    ],

    sidebar: [
      {
        text: 'Navigate',
        link: '/contents',
      },
      {
        text: 'About',
        link: '/meet-me',
      },
      {
        text: 'License',
        link: '/license',
      },
      {
        text: 'Notes',
        items: [
          { 
            text: 'Machine Learning',
            items: [
              { text: 'Compressed ImageNet', link: '/notes/machine-learning/compressed-imagenet' },
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
