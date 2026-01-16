<template>
  <div class="home-container">
    <div class="content-wrapper">
      <div class="header-actions">
        <el-dropdown @command="handleCommand">
          <span class="el-dropdown-link">
            <el-avatar :size="32" :icon="UserFilled" />
            <span class="username">{{ userStore.user?.username || '用户' }}</span>
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <h1 class="main-title"><span class="title-word">Testing</span> <span class="title-word">测试</span> <span class="title-word">平台</span></h1>
      <p class="subtitle">一站式智能化测试解决方案</p>
      
      <div class="cards-container" ref="cardsContainer">
        <!-- 用例管理 -->
        <div class="nav-card animate-on-scroll" @click="handleNavigate('ai')" role="button" tabindex="0">
          <div class="card-icon ai-icon">
            <el-icon><MagicStick /></el-icon>
          </div>
          <h3>用例管理</h3>
          <p>智能分析需求，自动生成测试用例</p>
        </div>

        <!-- 接口测试 -->
        <div class="nav-card animate-on-scroll" @click="handleNavigate('api')" role="button" tabindex="0">
          <div class="card-icon api-icon">
            <el-icon><Link /></el-icon>
          </div>
          <h3>接口测试</h3>
          <p>高效的接口自动化测试与管理</p>
        </div>

        <!-- UI自动化测试 -->
        <div class="nav-card animate-on-scroll" @click="handleNavigate('ui')" role="button" tabindex="0">
          <div class="card-icon ui-icon">
            <el-icon><Monitor /></el-icon>
          </div>
          <h3>UI自动化测试</h3>
          <p>可视化的Web/App UI自动化测试</p>
        </div>

        <!-- 数据工厂 -->
        <div class="nav-card animate-on-scroll" @click="handleNavigate('data')" role="button" tabindex="0">
          <div class="card-icon data-icon">
            <el-icon><DataLine /></el-icon>
          </div>
          <h3>数据工厂</h3>
          <p>灵活的测试数据构造与管理</p>
        </div>

        <!-- 自然语言Web测试 -->
        <div class="nav-card animate-on-scroll" @click="handleNavigate('midscene')" role="button" tabindex="0">
          <div class="card-icon midscene-icon">
            <el-icon><Message /></el-icon>
          </div>
          <h3>自然语言Web测试</h3>
          <p>AI驱动的UI自动化，支持自然语言操作</p>
        </div>
        <!-- 安全测试 -->
        <div class="nav-card animate-on-scroll" @click="handleNavigate('security')" role="button" tabindex="0">
          <div class="card-icon security-icon">
            <el-icon><Lock /></el-icon>
          </div>
          <h3>安全测试</h3>
          <p>基于Strix框架的安全漏洞扫描</p>
        </div>
        <!-- 性能测试 -->
        <div class="nav-card animate-on-scroll" @click="handleNavigate('performance')" role="button" tabindex="0">
          <div class="card-icon performance-icon">
            <el-icon><Timer /></el-icon>
          </div>
          <h3>性能测试</h3>
          <p>基于Locust的性能测试与压测</p>
        </div>
        <!-- 配置中心 -->
        <div class="nav-card animate-on-scroll" @click="handleNavigate('config')" role="button" tabindex="0">
          <div class="card-icon config-icon">
            <el-icon><Setting /></el-icon>
          </div>
          <h3>配置中心</h3>
          <p>系统环境、AI模型及通知配置</p>
        </div>
        
        <!-- 知识图谱 -->
        <div class="nav-card animate-on-scroll" @click="handleNavigate('knowledge-graph')" role="button" tabindex="0">
          <div class="card-icon knowledge-graph-icon">
            <el-icon><Connection /></el-icon>
          </div>
          <h3>知识图谱</h3>
          <p>基于RAG的多模态文档管理与知识图谱生成</p>
        </div>
        <!-- 智能化测试 -->
        <div class="nav-card animate-on-scroll" @click="handleNavigate('wharttest')" role="button" tabindex="0">
          <div class="card-icon wharttest-icon">
            <el-icon><DocumentChecked /></el-icon>
          </div>
          <h3>智能化测试</h3>
          <p>智能化测试功能模块，提供完整的测试解决方案</p>
        </div>
        


      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, Link, Monitor, DataLine, Cpu, Setting, ChatDotRound, UserFilled, ArrowDown, Message, Lock, Timer, Connection, DocumentChecked, Operation } from '@element-plus/icons-vue'
import { ref, onMounted, onBeforeUnmount } from 'vue'

const router = useRouter()
const userStore = useUserStore()
const cardsContainer = ref(null)
const observer = ref(null)

const handleCommand = (command) => {
  if (command === 'logout') {
    handleLogout()
  }
}

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    userStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  }).catch(() => {})
}

const handleNavigate = (type) => {
    const routes = {
      'ai': '/ai-generation/requirement-analysis',
      'api': '/api-testing/dashboard',
      'ui': '/ui-automation/dashboard',
      'config': '/configuration/ai-model',
      'midscene': '/midscene/dashboard',
      'security': '/strix-security/dashboard',
      'performance': '/performance-test/dashboard',
      'data': '/data-factory/dashboard',
      'knowledge-graph': '/knowledge-graph',
      'wharttest': '/wharttest/dashboard',
      'cicd': '/configuration/cicd-dashboard'
    }

    if (routes[type]) {
      router.push(routes[type])
    }
  }

// 滑动动画逻辑
const initScrollAnimation = () => {
  // 标题文字动画
  const titleWords = document.querySelectorAll('.title-word')
  titleWords.forEach((word, index) => {
    word.style.opacity = '0'
    word.style.transform = 'translateY(-20px)'
    word.style.transition = `all 0.6s ease ${index * 0.15}s`
    setTimeout(() => {
      word.style.opacity = '1'
      word.style.transform = 'translateY(0)'
    }, 100)
  })

  // 卡片滚动动画
  const options = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  }

  observer.value = new IntersectionObserver((entries) => {
    entries.forEach((entry, index) => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '0'
        entry.target.style.transform = 'translateY(30px)'
        entry.target.style.transition = `all 0.6s ease ${index * 0.1}s`
        
        setTimeout(() => {
          entry.target.style.opacity = '1'
          entry.target.style.transform = 'translateY(0)'
        }, 50)
        
        observer.value.unobserve(entry.target)
      }
    })
  }, options)

  const animatedElements = document.querySelectorAll('.animate-on-scroll')
  animatedElements.forEach(el => {
    observer.value.observe(el)
  })
}

onMounted(() => {
  initScrollAnimation()
})

onBeforeUnmount(() => {
  if (observer.value) {
    observer.value.disconnect()
  }
})
</script>

<style scoped lang="scss">
.home-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.content-wrapper {
  text-align: center;
  max-width: 1200px;
  width: 100%;
  position: relative;
}

.header-actions {
  position: absolute;
  top: 0;
  right: 0;
  padding: 10px;
  
  .el-dropdown-link {
    display: flex;
    align-items: center;
    cursor: pointer;
    color: #5e6d82;
    
    .username {
      margin: 0 8px;
      font-size: 14px;
    }
    
    &:hover {
      color: #409eff;
    }
  }
}

.main-title {
  font-size: 3.5rem;
  color: #2c3e50;
  margin-bottom: 1rem;
  font-weight: 700;
  letter-spacing: 2px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;

  .title-word {
    display: inline-block;
    opacity: 0;
    transform: translateY(-20px);
    transition: all 0.6s ease;
  }
}

.subtitle {
  font-size: 1.5rem;
  color: #5e6d82;
  margin-bottom: 4rem;
  opacity: 0;
  transform: translateY(20px);
  animation: fadeInUp 0.8s ease 0.5s forwards;
}

.cards-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
  padding: 20px;
}

.nav-card {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 16px;
  padding: 40px 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  align-items: center;
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.6s ease;

  &:hover {
    transform: translateY(-10px) scale(1.02);
    box-shadow: 0 20px 30px rgba(0, 0, 0, 0.1);
    background: #fff;
  }

  h3 {
    font-size: 1.5rem;
    color: #2c3e50;
    margin: 20px 0 10px;
  }

  p {
    color: #7f8c8d;
    line-height: 1.5;
    margin: 0;
  }
}

/* 动画效果 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 滚动时的动画 */
.animate-on-scroll {
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.6s ease;
}

.card-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  margin-bottom: 10px;
  transition: all 0.3s ease;

  &.ai-icon {
    background: #e8f4ff;
    color: #409eff;
  }

  &.api-icon {
    background: #f0f9eb;
    color: #67c23a;
  }

  &.ui-icon {
    background: #fdf6ec;
    color: #e6a23c;
  }

  &.data-icon {
    background: #f4f4f5;
    color: #909399;
  }

  &.ai-intelligent-icon {
    background: #f0f5ff;
    color: #2f54eb;
  }

  &.config-icon {
    background: #e6fffb;
    color: #13c2c2;
  }

  &.assistant-icon {
    background: #fff7e6;
    color: #fa8c16;
  }

  &.midscene-icon {
    background: #f0f0ff;
    color: #722ed1;
  }

  &.security-icon {
    background: #fff2f0;
    color: #f56c6c;
  }

  &.performance-icon {
    background: #f6ffed;
    color: #52c41a;
  }

  &.knowledge-graph-icon {
    background: #e6f7ff;
    color: #1890ff;
  }

  &.wharttest-icon {
    background: #fff1f0;
    color: #eb2f96;
  }

  &.cicd-icon {
    background: #e6f7ff;
    color: #1890ff;
  }
}

.nav-card:hover .card-icon {
  transform: scale(1.1);
}
</style>
