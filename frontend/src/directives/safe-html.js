import sanitizeHtml from '@/utils/sanitize'

// 全局指令 v-safe-html：渲染前对 HTML 进行 DOMPurify 净化，防止 XSS。
// 用法：<div v-safe-html="rawHtml"></div>
const safeHtmlDirective = {
  mounted(el, binding) {
    el.innerHTML = sanitizeHtml(binding.value)
  },
  updated(el, binding) {
    el.innerHTML = sanitizeHtml(binding.value)
  },
}

export default safeHtmlDirective
