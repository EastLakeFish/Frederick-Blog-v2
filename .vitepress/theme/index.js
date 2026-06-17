// .vitepress/theme/index.js
import DefaultTheme from 'vitepress/theme'

// import css
import './style/custom.css'
import './style/contact.css'
import './style/contents.css'
import './style/figures.css'
import './style/home.css'
import './style/lightbox.css'
import './style/reference.css'
import './style/sourceindex.css'
import './style/sourcefile.css'
import './style/sourcefileblock.css'
import './style/sourceviewer.css'
import './style/update-notes.css'

// import components
import { onMounted } from 'vue'
import { setupLightbox } from './components/lightbox.ts'

import Contents from './components/contents.vue'
import Layout from './components/icpfooter.vue'
import References from './components/reference.vue'
import SourceIndex from './components/sourceindex.vue'
import SourceFile from './components/sourcefile.vue'
import SourceViewer from './components/sourceviewer.vue'

export default {

  extends: DefaultTheme,

  Layout,  // ICPFooter Layout

  setup() {
    onMounted(() => {
      setupLightbox()
    })
  },

  enhanceApp({ app }) {
    app.component('Contents', Contents)
    app.component('References', References)
    app.component('SourceIndex', SourceIndex)
    app.component('SourceFile', SourceFile)
    app.component('SourceViewer', SourceViewer)
  },

}