<template>
  <div class="login-container">
    <div class="background-animate"></div>
    
    <div class="login-card glass-effect">
      <div class="login-header">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h1>Testing Platform</h1>
        <p>智能化全栈测试解决方案</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        @submit.prevent="handleLogin"
        class="login-form"
        size="large"
      >
        <el-form-item prop="username">
          <el-input 
            v-model="form.username" 
            placeholder="用户名 / 邮箱"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <div class="form-actions">
          <el-checkbox v-model="rememberMe">记住我</el-checkbox>
          <el-link type="primary" :underline="false">忘记密码?</el-link>
        </div>

        <el-button 
          type="primary" 
          class="submit-btn" 
          :loading="loading" 
          @click="handleLogin"
        >
          {{ loading ? '登录中...' : '登 录' }}
        </el-button>
        
        <!-- 注册链接 -->
        <div class="register-link">
          还没有账号? <router-link to="/register">立即注册</router-link>
        </div>
      </el-form>
    </div>
    
    <div class="footer-copyright">
      &copy; {{ new Date().getFullYear() }} Testing Platform. All rights reserved.
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)
const rememberMe = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await userStore.login(form)
        ElMessage.success('欢迎回来')
        router.replace('/home')
      } catch (error) {
        ElMessage.error(error.response?.data?.error || '登录失败，请检查用户名或密码')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style lang="scss" scoped>
.login-container {
  height: 100vh;
  width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: #0f172a; /* Fallback */
}

.background-animate {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(125deg, #0f172a 0%, #1e1b4b 30%, #312e81 60%, #4338ca 100%);
  background-size: 400% 400%;
  animation: gradientBG 15s ease infinite;
  z-index: 0;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.05) 0%, transparent 60%);
    pointer-events: none;
  }
}

.login-card {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 420px;
  padding: 48px 40px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
  
  .logo-icon {
    width: 64px;
    height: 64px;
    margin: 0 auto 16px;
    color: #818cf8;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 12px;
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
    
    svg {
      width: 100%;
      height: 100%;
    }
  }
  
  h1 {
    font-size: 28px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 8px;
    letter-spacing: -0.5px;
  }
  
  p {
    color: #94a3b8;
    font-size: 15px;
  }
}

.login-form {
  :deep(.el-input__wrapper) {
    background: rgba(0, 0, 0, 0.2) !important;
    box-shadow: none !important;
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 12px 15px;
    
    &.is-focus {
      border-color: #818cf8;
      background: rgba(0, 0, 0, 0.3) !important;
    }
    
    input {
      color: #fff;
      &::placeholder {
        color: #64748b;
      }
    }
    
    .el-input__icon {
      color: #94a3b8;
    }
  }
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  
  :deep(.el-checkbox__label) {
    color: #94a3b8;
  }
  
  :deep(.el-checkbox__inner) {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
  }
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  border-radius: 12px !important;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
  border: none;
  box-shadow: 0 10px 20px -5px rgba(99, 102, 241, 0.4);
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 15px 25px -5px rgba(99, 102, 241, 0.5);
  }
}

.register-link {
  text-align: center;
  margin-top: 24px;
  color: #94a3b8;
  font-size: 14px;
  
  a {
    color: #818cf8;
    font-weight: 600;
    margin-left: 5px;
    
    &:hover {
      color: #a5b4fc;
      text-decoration: underline;
    }
  }
}

.footer-copyright {
  position: absolute;
  bottom: 24px;
  color: rgba(255, 255, 255, 0.2);
  font-size: 12px;
  z-index: 10;
}

@keyframes gradientBG {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(40px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
