import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/utils/api'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  // 安全说明：Token 不再写入 localStorage（防止 XSS 窃取）。
  // 仅保留在 Pinia 内存中；持久化需后端配合写入 httpOnly Cookie。
  const accessToken = ref('')
  const refreshToken = ref('')
  const tokenExpiresAt = ref(0)
  // 当前用户角色列表（用于前端 RBAC）。需后端在 /users/me/ 响应中返回 roles 字段。
  const userRoles = ref([])

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)

  // 检查token是否即将过期（5分钟内）
  const isTokenExpiringSoon = computed(() => {
    if (!tokenExpiresAt.value) return false
    const now = Date.now()
    const timeLeft = tokenExpiresAt.value - now
    return timeLeft < 5 * 60 * 1000 // 5分钟
  })

  // 检查token是否已过期
  const isTokenExpired = computed(() => {
    if (!tokenExpiresAt.value) return false
    return Date.now() > tokenExpiresAt.value
  })

  const login = async (credentials) => {
    try {
      const response = await api.post('/users/login/', credentials)

      // 保存双token
      accessToken.value = response.data.access
      refreshToken.value = response.data.refresh
      user.value = response.data.user

      // 计算过期时间（当前时间 + 60分钟，与后端配置一致）
      const expiresAt = Date.now() + 60 * 60 * 1000
      tokenExpiresAt.value = expiresAt

      // 注意：不再写入 localStorage（XSS 防护）。如需持久化，由后端写入 httpOnly Cookie。
      return response.data
    } catch (error) {
      throw error
    }
  }

  const register = async (userData) => {
    try {
      // 临时使用测试接口
      const response = await api.post('/users/test-register/', userData)

      // 保存双token
      accessToken.value = response.data.access || response.data.token
      refreshToken.value = response.data.refresh || ''
      user.value = response.data.user

      // 计算过期时间（当前时间 + 60分钟，与后端配置一致）
      const expiresAt = Date.now() + 60 * 60 * 1000
      tokenExpiresAt.value = expiresAt

      // 注意：不再写入 localStorage（XSS 防护）。如需持久化，由后端写入 httpOnly Cookie。
      return response.data
    } catch (error) {
      throw error
    }
  }

  // 添加一个标记防止logout过程中的循环调用
  let isLoggingOut = false

  const logout = async () => {
    // 防止重复调用logout
    if (isLoggingOut) {
      return
    }
    isLoggingOut = true

    try {
      // 只有当access token未过期时，才尝试调用logout API将refresh token加入黑名单
      // 如果token已过期，直接清除本地状态即可，避免401死循环
      if (refreshToken.value && !isTokenExpired.value) {
        try {
          await api.post('/users/logout/', { refresh: refreshToken.value })
        } catch (apiError) {
          // logout API调用失败不影响本地清除操作
          console.error('Logout API调用失败:', apiError)
        }
      }
    } finally {
      // 清除所有认证信息
      accessToken.value = ''
      refreshToken.value = ''
      user.value = null
      tokenExpiresAt.value = 0

      // 注意：不再清理 localStorage（已无 token 写入）。

      // 重置标记
      isLoggingOut = false

      window.location.href = '/login'
    }
  }

  // 刷新access token
  const refreshAccessToken = async () => {
    try {
      const response = await api.post('/users/token/refresh/', {
        refresh: refreshToken.value
      })

      // 更新access token和过期时间
      accessToken.value = response.data.access
      const expiresAt = Date.now() + 30 * 60 * 1000
      tokenExpiresAt.value = expiresAt

      // 如果返回了新的refresh token（启用了ROTATE_REFRESH_TOKENS）
      if (response.data.refresh) {
        refreshToken.value = response.data.refresh
      }

      // 注意：不再写入 localStorage（XSS 防护）。

      return response.data.access
    } catch (error) {
      // 刷新失败，清除所有认证信息
      console.error('Token refresh failed:', error)
      await logout()
      throw error
    }
  }

  // 冷启动会话恢复：利用后端下发的 httpOnly Refresh Cookie 自动续期。
  // 关键点：前端不读取、不写入 localStorage（XSS 防护）；Refresh Token 存于 httpOnly Cookie，
  // 请求带 credentials: 'include'（axios 即 withCredentials: true），浏览器自动附带该 Cookie。
  // 后端 TokenRefreshView 在请求体无 refresh 时自动从 Cookie 读取并签发新 access token。
  const restoreSession = async () => {
    try {
      const response = await api.post(
        '/users/token/refresh/',
        {},
        { withCredentials: true }
      )

      if (response.data && response.data.access) {
        accessToken.value = response.data.access
        // access_token 有效期 60 分钟（与后端 ACCESS_TOKEN_LIFETIME 一致）
        tokenExpiresAt.value = Date.now() + 60 * 60 * 1000
        // 若后端启用 ROTATE_REFRESH_TOKENS，响应会带回新 refresh（仍在内存，不落 localStorage）
        if (response.data.refresh) {
          refreshToken.value = response.data.refresh
        }
        return response.data.access
      }
      throw new Error('Refresh response missing access token')
    } catch (error) {
      // 恢复失败：保持登出，清空内存状态（不写 localStorage）
      accessToken.value = ''
      refreshToken.value = ''
      user.value = null
      tokenExpiresAt.value = 0
      throw error
    }
  }

  const fetchUser = async () => {
    try {
      const response = await api.get('/users/me/')
      user.value = response.data
      // 注意：不再写入 localStorage（XSS 防护）。
    } catch (error) {
      await logout()
      throw error
    }
  }

  const fetchProfile = async () => {
    try {
      const response = await api.get('/users/profile/')
      user.value = response.data
      // 注意：不再写入 localStorage（XSS 防护）。
      return response.data
    } catch (error) {
      if (error.response?.status === 401) {
        await logout()
      }
      throw error
    }
  }

  const initAuth = async () => {
    console.log('initAuth 开始:', {
      hasAccessToken: !!accessToken.value,
      hasRefreshToken: !!refreshToken.value,
      hasUser: !!user.value,
      isExpired: isTokenExpired.value
    })

    // 注意：不再从 localStorage 恢复用户信息（Token 已不在前端持久化）。
    // 如需“刷新后保持登录”，应由后端写入 httpOnly Cookie，前端凭 Cookie 自动携带。

    if (accessToken.value) {
      // 检查token是否过期
      if (isTokenExpired.value && refreshToken.value) {
        console.log('Token已过期，尝试刷新...')
        try {
          await refreshAccessToken()
          console.log('Token刷新成功')
        } catch (error) {
          console.error('Token刷新失败:', error)
          return
        }
      }

      // 获取用户信息
      if (!user.value) {
        try {
          console.log('获取用户信息...')
          await fetchProfile()
          console.log('用户信息获取成功:', user.value?.username)
        } catch (error) {
          console.error('获取用户信息失败:', error)
          await logout()
        }
      } else {
        console.log('用户信息已存在，跳过获取')
      }
    } else {
      console.log('没有access token，跳过认证初始化')
    }
  }

  // 获取当前用户角色（用于前端 RBAC 守卫，fail-closed）。
  // 调用权限接口 /users/me/，从响应中提取 roles（角色 code 数组）。
  // 需后端在 /users/me/ 响应中返回 roles 字段；若缺失，roles 为空（即无权限）。
  const loadUserRoles = async () => {
    const res = await api.get('/users/me/')
    const data = res.data || {}
    const roles = data.roles || (data.user && data.user.roles) || []
    userRoles.value = Array.isArray(roles) ? roles : []
    return userRoles.value
  }

  return {
    user,
    accessToken,
    refreshToken,
    tokenExpiresAt,
    userRoles,
    isAuthenticated,
    isTokenExpiringSoon,
    isTokenExpired,
    login,
    register,
    logout,
    refreshAccessToken,
    restoreSession,
    fetchProfile,
    initAuth,
    loadUserRoles
  }
})
