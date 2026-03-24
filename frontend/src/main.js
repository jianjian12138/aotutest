import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import axios from 'axios'
import { useUserStore } from '@/stores/user'

import App from './App.vue'
import router from './router'
import './assets/css/global.scss'
import BasePage from '@/components/BasePage/index.vue'
import PremiumCard from '@/components/Premium/PremiumCard.vue'
import PremiumButton from '@/components/Premium/PremiumButton.vue'

// Axios 基础配置
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';
axios.defaults.withCredentials = true; // 允许跨域请求携带 Cookie

const app = createApp(App)

app.use(createPinia())

const userStore = useUserStore()

async function init() {
  try {
    await userStore.initAuth()
  } catch (error) {
    // 获取用户信息失败，说明未登录，无需处理
  }

  // 注册所有图标
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }

  app.use(router)
  app.use(ElementPlus, {
    locale: zhCn,
  })

  // 注册全局通用布局组件
  app.component('BasePage', BasePage)
  app.component('PremiumCard', PremiumCard)
  app.component('PremiumButton', PremiumButton)

  app.mount('#app')
}

init()

