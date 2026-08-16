import { ref } from 'vue'

/**
 * 统一处理后端「本期未交付」响应（200 + {status:'not_implemented'}）。
 * 用法：在页面中 const { notImplemented, implMeta, check } = useNotImplemented()
 *       调接口后 check(res) —— 命中则返回 true 并把负载写入 implMeta。
 */
export function isNotImplemented(resp) {
  const data = resp && (resp.data || resp)
  return !!(data && typeof data === 'object' && data.status === 'not_implemented')
}

export function useNotImplemented() {
  const notImplemented = ref(false)
  const implMeta = ref(null)

  function check(resp) {
    if (isNotImplemented(resp)) {
      notImplemented.value = true
      implMeta.value = (resp && resp.data) || resp
      return true
    }
    return false
  }

  return { notImplemented, implMeta, check }
}
