/**
 * 通用工具函数
 * 封装项目中重复使用的工具方法
 */

/**
 * 格式化日期时间
 * @param {string|Date} date - 日期对象或字符串
 * @param {string} format - 格式模板，默认 'YYYY-MM-DD HH:mm:ss'
 */
export function formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
  if (!date) return ''
  
  const d = new Date(date)
  if (isNaN(d.getTime())) return ''
  
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')
  
  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * 格式化相对时间（如：3 小时前）
 * @param {string|Date} date - 日期对象或字符串
 */
export function formatTime(date) {
  if (!date) return ''
  
  const d = new Date(date)
  const now = new Date()
  const diff = now - d
  
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  const months = Math.floor(days / 30)
  const years = Math.floor(months / 12)
  
  if (years > 0) return `${years}年前`
  if (months > 0) return `${months}个月前`
  if (days > 0) return `${days}天前`
  if (hours > 0) return `${hours}小时前`
  if (minutes > 0) return `${minutes}分钟前`
  if (seconds > 0) return `${seconds}秒前`
  return '刚刚'
}

/**
 * 获取状态标签类型（Element Plus）
 * @param {string|number} status - 状态值
 * @param {Object} mapping - 状态映射配置
 */
export function getStatusTagType(status, mapping = {}) {
  const defaultMapping = {
    'success': ['success', 'completed', 'done', 'passed'],
    'warning': ['warning', 'pending', 'waiting'],
    'danger': ['danger', 'failed', 'error', 'failure'],
    'info': ['info', 'unknown']
  }
  
  const map = { ...defaultMapping, ...mapping }
  
  for (const [type, values] of Object.entries(map)) {
    if (values.includes(status)) return type
  }
  
  return ''
}

/**
 * 获取状态文本
 * @param {string|number} status - 状态值
 * @param {Object} mapping - 状态映射配置
 */
export function getStatusText(status, mapping = {}) {
  const defaultMapping = {
    '成功': ['success', 'completed', 'done', 'passed'],
    '警告': ['warning', 'pending', 'waiting'],
    '失败': ['danger', 'failed', 'error', 'failure'],
    '未知': ['info', 'unknown']
  }
  
  const map = { ...defaultMapping, ...mapping }
  
  for (const [text, values] of Object.entries(map)) {
    if (values.includes(status)) return text
  }
  
  return status
}

/**
 * 防抖函数
 * @param {Function} func - 需要防抖的函数
 * @param {number} delay - 延迟时间（毫秒）
 */
export function debounce(func, delay = 300) {
  let timer = null
  return function(...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      func.apply(this, args)
    }, delay)
  }
}

/**
 * 节流函数
 * @param {Function} func - 需要节流的函数
 * @param {number} delay - 延迟时间（毫秒）
 */
export function throttle(func, delay = 300) {
  let lastTime = 0
  return function(...args) {
    const now = Date.now()
    if (now - lastTime >= delay) {
      func.apply(this, args)
      lastTime = now
    }
  }
}

/**
 * 深拷贝（简单实现）
 * @param {*} obj - 需要拷贝的对象
 */
export function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj
  if (obj instanceof Date) return new Date(obj)
  if (obj instanceof Array) return obj.map(item => deepClone(item))
  if (obj instanceof Object) {
    const clonedObj = {}
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key])
      }
    }
    return clonedObj
  }
  return obj
}
