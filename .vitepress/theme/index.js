// .vitepress/theme/index.js
import DefaultTheme from 'vitepress/theme'

// import css
import './custom.css'
import './contact.css'
import './contents.css'
import './figures.css'
import './home.css'
import './lightbox.css'
import './reference.css'

// import functions
import { onMounted } from 'vue'
import { setupLightbox } from './lightbox'
import References from './reference.vue'

export default {

  extends: DefaultTheme,

  setup() {
    onMounted(() => {
      setupLightbox()
    })
  },

  enhanceApp({ app }) {
    app.component('References', References)
  }

}