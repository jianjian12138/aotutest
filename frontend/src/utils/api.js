import axios from 'axios'
import { ElMessage } from 'element-plus'
// Remove top-level import to avoid circular dependency with user store
// import { useUserStore } from '@/stores/user'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 正在刷新的标志
let isRefreshing = false
// 等待刷新的请求队列
let failedQueue = []

// 处理队列中的请求
const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })

  failedQueue = []
}

// 请求拦截器
api.interceptors.request.use(
  async (config) => {
    // Dynamically import user store to avoid circular dependency
    const { useUserStore } = await import('@/stores/user')
    const userStore = useUserStore()

    // 检查是否是刷新token的请求
    if (config.url === '/users/token/refresh/') {
      return config
    }

    // 如果有access token
    if (userStore.accessToken) {
      // 检查token是否即将过期（5分钟内）
      if (userStore.isTokenExpiringSoon && !userStore.isTokenExpired) {
        // 如果没有正在刷新，开始刷新
        if (!isRefreshing) {
          isRefreshing = true
          console.log('Token即将过期，开始刷新...')

          try {
            const newToken = await userStore.refreshAccessToken()
            console.log('Token刷新成功')
            processQueue(null, newToken)

            // 更新当前请求的token
            config.headers.Authorization = `Bearer ${newToken}`
          } catch (error) {
            console.error('Token刷新失败:', error)
            processQueue(error, null)
            // 刷新失败会在user store中自动logout
            return Promise.reject(error)
          } finally {
            isRefreshing = false
          }
        } else {
          // 如果正在刷新，将请求加入队列并等待
          console.log('Token正在刷新，请求加入队列等待...')
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject })
          }).then(token => {
            // 更新当前请求的token
            config.headers.Authorization = `Bearer ${token}`
            return config
          }).catch(err => {
            return Promise.reject(err)
          })
        }
      } else {
        // 使用现有token
        config.headers.Authorization = `Bearer ${userStore.accessToken}`
      }
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    // V2 Standard Response Unwrapper
    const resData = response.data
    // 检查是否为 V2 统一格式: 具有 code, trace_id, 且为成功状态
    if (resData && typeof resData === 'object' && 'trace_id' in resData && 'code' in resData) {
        if (resData.code >= 200 && resData.code < 300) {
            // 平铺数据层，完美兼容 V1 组件调用
            response.data = resData.data
        }
    }
    return response
  },
  async (error) => {
    // Dynamically import user store to avoid circular dependency
    const { useUserStore } = await import('@/stores/user')
    const userStore = useUserStore()
    const originalRequest = error.config

    // 如果是401错误且不是刷新token的请求
    if (error.response?.status === 401 && !originalRequest._retry) {
      // 如果是logout请求失败，直接清除本地状态不再重试logout，防止死循环
      if (originalRequest.url === '/users/logout/') {
        console.error('Logout请求401，直接清除本地状态')
        userStore.$patch((state) => {
          state.accessToken = ''
          state.refreshToken = ''
          state.user = null
          state.tokenExpiresAt = 0
        })
        // 注意：Token 不再存于 localStorage，仅需清除 Pinia 状态（已在上方完成）。
        // 如果没有refresh token或刷新失败，跳转登录
        await userStore.logout()
        // 删除以下强制跳转，让store去处理
        // window.location.href = '/login'
        return Promise.reject(error)
      }

      // 如果是刷新token的请求失败
      if (originalRequest.url === '/users/token/refresh/') {
        console.error('Refresh token失败，跳转登录页')
        await userStore.logout()
        return Promise.reject(error)
      }

      // 收到401：用后端 httpOnly Refresh Cookie 续期（前端不读取、不写 localStorage）。
      // 刷新后内存中的 refreshToken 为空，无法再用请求体刷新，必须依赖浏览器自动附带的 Cookie。
      if (!isRefreshing) {
        originalRequest._retry = true
        isRefreshing = true

        try {
          console.log('收到401响应，尝试用 Refresh Cookie 续期...')
          // restoreSession 内部以 withCredentials 发起请求，浏览器自动附带 refresh_token Cookie
          const newToken = await userStore.restoreSession()
          console.log('会话续期成功，重试原请求')
          processQueue(null, newToken)

          // 更新当前请求的token
          originalRequest.headers.Authorization = `Bearer ${newToken}`

          // 重试原请求
          return api(originalRequest)
        } catch (refreshError) {
          console.error('Refresh Cookie 续期失败:', refreshError)
          processQueue(refreshError, null)
          // restoreSession 已清空内存状态；这里执行登出（清除并跳登录）
          await userStore.logout()
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      } else {
        // 正在刷新，将请求加入队列等待新 token
        console.log('会话续期中，请求加入队列等待...')
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        }).catch(err => Promise.reject(err))
      }

      return Promise.reject(error)
    }

    // 其他错误处理 (Global Error Handler for non-401s)
    if (error.response && error.response.status !== 401) {
      let errorMsg = '请求失败，请稍后重试'
      if (error.response.status >= 500) {
        errorMsg = '服务器错误，请联系管理员或稍后重试'
      } else if (error.response.data) {
        let rawData = error.response.data
        //如果是V2返回标准格式，提取真正的报错内容
        if (rawData && typeof rawData === 'object' && 'trace_id' in rawData && 'code' in rawData) {
            rawData = rawData.data || rawData
        }

        if (typeof rawData.error === 'string') {
          errorMsg = rawData.error
        } else if (typeof rawData.detail === 'string') {
          errorMsg = rawData.detail
        } else if (typeof rawData.message === 'string') {
          errorMsg = rawData.message
        } else if (typeof rawData === 'string' && rawData.length < 100) {
          errorMsg = rawData
        } else if (typeof rawData === 'object') {
          // Parse typical DRF field validation errors mapping
          const msgs = []
          for (const key in rawData) {
            if (Array.isArray(rawData[key])) {
              msgs.push(`${key}: ${rawData[key].join(', ')}`)
            }
          }
          if (msgs.length > 0) errorMsg = msgs.join(' | ')
        }
      }
      
      ElMessage({
        message: errorMsg,
        type: 'error',
        duration: 5000,
        showClose: true
      })
    } else if (error.response?.status === 401 && !originalRequest._retry) {
      ElMessage.error('登录已过期，请重新登录')
    } else if (!error.response) {
      // Network error or timeout
      ElMessage({
        message: '网络异常或服务器无响应，请检查网络连接',
        type: 'error',
        duration: 5000,
        showClose: true
      })
    }

    return Promise.reject(error)
  }
)

// ── 全局 axios 认证拦截器 ───────────────────────────────
// 让裸 axios（未使用 api 实例）的请求也自动携带 Bearer Token，
// 避免后端升级为 IsAuthenticated 后，这些前端调用全部收到 401。
// 注意：Token 仅存于 Pinia（内存），不再从 localStorage 读取（XSS 防护）。
axios.interceptors.request.use(
  async (config) => {
    const headers = config.headers || {}
    // 动态导入 user store，避免循环依赖
    const { useUserStore } = await import('@/stores/user')
    const userStore = useUserStore()
    const token = userStore.accessToken
    if (token && !(headers.Authorization || headers.authorization)) {
      headers.Authorization = `Bearer ${token}`
    }
    config.headers = headers
    return config
  },
  (error) => Promise.reject(error)
)

// ── 裸 fetch 认证助手 ──────────────────────────────────
// 供未使用 api 实例的 fetch 调用附加认证头。
// 注意：Token 仅存于 Pinia（内存），不再从 localStorage 读取（XSS 防护）。
// 调用方可直接传入 Authorization 头；未传入时从 user store 动态读取 token。
export async function authFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (!(headers.Authorization || headers.authorization)) {
    try {
      // 动态导入 user store，避免循环依赖
      const { useUserStore } = await import('@/stores/user')
      const userStore = useUserStore()
      if (userStore && userStore.accessToken) {
        headers.Authorization = `Bearer ${userStore.accessToken}`
      }
    } catch (e) {
      // 忽略：无法获取 token 时不附加 Authorization
    }
  }
  return fetch(url, { ...options, headers })
}

export default api
