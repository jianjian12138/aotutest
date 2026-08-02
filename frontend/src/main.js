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
import safeHtmlDirective from '@/directives/safe-html'
import './assets/css/global.scss'
import BasePage from '@/components/BasePage/index.vue'
import PremiumCard from '@/components/Premium/PremiumCard.vue'
import PremiumButton from '@/components/Premium/PremiumButton.vue'

// V2.0 P1 Performance Enhancement
import VueVirtualScroller from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'

// Axios 基础配置
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';
axios.defaults.withCredentials = true; // 允许跨域请求携带 Cookie

const app = createApp(App)

app.use(createPinia())

const userStore = useUserStore()

async function init() {
  try {
    // 应用冷启动：先尝试用后端 httpOnly Refresh Cookie 恢复会话（不写 localStorage）。
    // 成功则写入 Pinia 内存；失败则保持未登录，由路由守卫导向 /login。
    await userStore.restoreSession()
  } catch (error) {
    // 无有效 Refresh Cookie，保持登出状态，无需处理
  }

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
  app.use(VueVirtualScroller)

  // 注册全局指令：v-safe-html（XSS 防护，渲染前净化 HTML）
  app.directive('safe-html', safeHtmlDirective)

  // 注册全局通用布局组件
  app.component('BasePage', BasePage)
  app.component('PremiumCard', PremiumCard)
  app.component('PremiumButton', PremiumButton)

  app.mount('#app')
}

init()

