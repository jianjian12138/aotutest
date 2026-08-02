import DOMPurify from 'dompurify'

// XSS 防护：对渲染前的 HTML 进行净化，只允许安全的基础 HTML 标签与属性。
// 用法：sanitizeHtml(rawHtml)；配合 v-safe-html 指令使用。
export default function sanitizeHtml(html) {
  return DOMPurify.sanitize(html ?? '', { USE_PROFILES: { html: true } })
}
