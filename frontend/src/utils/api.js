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
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
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

      // 如果有refresh token，尝试刷新
      if (userStore.refreshToken && !isRefreshing) {
        originalRequest._retry = true
        isRefreshing = true

        try {
          console.log('收到401响应，尝试刷新token...')
          const newToken = await userStore.refreshAccessToken()
          console.log('Token刷新成功，重试原请求')
          processQueue(null, newToken)

          // 更新当前请求的token
          originalRequest.headers.Authorization = `Bearer ${newToken}`

          // 重试原请求
          return api(originalRequest)
        } catch (refreshError) {
          console.error('Token刷新失败:', refreshError)
          processQueue(refreshError, null)
          await userStore.logout()
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      } else {
        // 没有refresh token，直接退出
        console.error('没有refresh token，跳转登录页')
        await userStore.logout()
      }

      return Promise.reject(error)
    }

    // 其他错误处理 (Global Error Handler for non-401s)
    if (error.response && error.response.status !== 401) {
      let errorMsg = '请求失败，请稍后重试'
      if (error.response.status >= 500) {
        errorMsg = '服务器错误，请联系管理员或稍后重试'
      } else if (error.response.data) {
        const data = error.response.data
        if (typeof data.error === 'string') {
          errorMsg = data.error
        } else if (typeof data.detail === 'string') {
          errorMsg = data.detail
        } else if (typeof data.message === 'string') {
          errorMsg = data.message
        } else if (typeof data === 'string' && data.length < 100) {
          errorMsg = data
        } else if (typeof data === 'object') {
          // Parse typical DRF field validation errors mapping
          const msgs = []
          for (const key in data) {
            if (Array.isArray(data[key])) {
              msgs.push(`${key}: ${data[key].join(', ')}`)
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

export default api
