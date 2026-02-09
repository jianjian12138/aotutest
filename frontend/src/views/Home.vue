<template>
  <div class="home-container">
    <!-- 顶部用户信息栏 -->
    <div class="home-user-bar" v-if="userStore.user">
      <el-dropdown placement="bottom-end">
        <span class="user-trigger">
          <div class="avatar">{{ avatarInitials }}</div>
          <span class="username">{{ displayName }}</span>
          <el-icon class="arrow-icon"><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="router.push('/configuration/profile')">个人中心</el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div class="orbit-scene">
      <!-- 中心核心区域 -->
      <div class="center-core">
        <div class="core-glow"></div>
        <div class="core-content">
          <h1>Testing<br />Platform</h1>
          <p>智能测试平台</p>
        </div>
      </div>

      <!-- 旋转轨道容器 -->
      <div
        class="orbit-ring"
        :class="{ paused: isPaused }"
        @mouseenter="isPaused = true"
        @mouseleave="isPaused = false"
      >
        <!-- 轨道线 -->
        <div class="orbit-line"></div>

        <!-- 围绕的菜单项 -->
        <div
          v-for="(card, index) in allCards"
          :key="card.type"
          class="orbit-item"
          :style="getItemStyle(index)"
          @click="handleNavigate(card.type)"
        >
          <div class="planet-card">
            <div class="planet-icon" :class="card.iconClass">
              <el-icon><component :is="card.icon" /></el-icon>
            </div>
            <div class="planet-info">
              <h3>{{ card.title }}</h3>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="footer-tips">
      <el-icon><Mouse /></el-icon>
      悬停停止转动，点击进入模块
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  MagicStick,
  Link,
  Monitor,
  DataLine,
  Cpu,
  Setting,
  Mouse,
  Connection,
  DocumentChecked,
  Operation,
  ArrowDown
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const isPaused = ref(false)

const allCards = [
  { type: 'case', title: '需求与用例', icon: DocumentChecked, iconClass: 'case-icon' },
  { type: 'api', title: '接口测试', icon: Link, iconClass: 'api-icon' },
  { type: 'ui', title: 'UI自动化', icon: Monitor, iconClass: 'ui-icon' },
  { type: 'midscene', title: '自然语言测试', icon: Operation, iconClass: 'midscene-icon' },
  { type: 'security', title: '安全测试', icon: Cpu, iconClass: 'security-icon' },
  { type: 'knowledge', title: '知识图谱', icon: MagicStick, iconClass: 'knowledge-icon' },
  { type: 'data', title: '数据工厂', icon: DataLine, iconClass: 'data-icon' },
  { type: 'performance', title: '性能测试', icon: Cpu, iconClass: 'performance-icon' },
  { type: 'config', title: '配置中心', icon: Setting, iconClass: 'config-icon' }
]

const totalItems = allCards.length
const radius = 320

// 计算每个星球的位置
const getItemStyle = (index) => {
  const angle = (360 / totalItems) * index
  return {
    '--rotate-angle': `${angle}deg`,
    '--counter-angle': `-${angle}deg`
  }
}

const avatarInitials = computed(() => {
  const u = userStore.user
  if (!u) return ''
  const base = u.username || u.email || ''
  return base.slice(0, 2).toUpperCase()
})

const displayName = computed(() => {
  const u = userStore.user
  if (!u) return ''
  return u.username || u.email || '用户'
})

const handleLogout = async () => {
  await userStore.logout()
}

const handleNavigate = (type) => {
  const routes = {
    case: '/ai-generation/testcases',
    api: '/api-testing/dashboard',
    ui: '/ui-automation/dashboard',
    midscene: '/natural-language-testing/web-testing',
    security: '/strix-security/dashboard',
    knowledge: '/knowledge-graph/dashboard',
    data: '/data-factory/dashboard',
    performance: '/performance-test/dashboard',
    config: '/configuration/ai-model'
  }

  if (routes[type]) {
    router.push(routes[type])
  }
}
</script>

<style lang="scss" scoped>
.home-container {
  height: 100vh;
  width: 100%;
  background-color: #0f172a;
  background-image: radial-gradient(circle at center, #1e293b 0%, #0f172a 70%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  perspective: 1000px;
  position: relative;
}

.home-user-bar {
  position: absolute;
  top: 20px;
  right: 32px;
  z-index: 20;

  .user-trigger {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 6px 12px;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(148, 163, 184, 0.3);
    cursor: pointer;
    color: #e5e7eb;
    backdrop-filter: blur(8px);
  }

  .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
    color: #f9fafb;
  }

  .username {
    font-size: 14px;
    font-weight: 500;
  }

  .arrow-icon {
    font-size: 14px;
  }
}

.orbit-scene {
  position: relative;
  width: 800px;
  height: 800px;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 中心核心 */
.center-core {
  position: absolute;
  width: 200px;
  height: 200px;
  z-index: 10;
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
  
  .core-glow {
    position: absolute;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.2) 0%, transparent 70%);
    box-shadow: 0 0 60px rgba(99, 102, 241, 0.3);
    animation: pulse 3s infinite ease-in-out;
  }
  
  .core-content {
    position: relative;
    z-index: 2;
    
    h1 {
      font-size: 32px;
      font-weight: 800;
      line-height: 1.1;
      margin-bottom: 8px;
      background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      text-shadow: 0 0 20px rgba(99, 102, 241, 0.5);
    }
    
    p {
      color: #94a3b8;
      font-size: 14px;
      letter-spacing: 2px;
      text-transform: uppercase;
    }
  }
}

/* 轨道环 */
.orbit-ring {
  position: absolute;
  width: 640px; /* 2 * radius */
  height: 640px;
  border-radius: 50%;
  animation: orbit-rotate 60s linear infinite;
  transform-origin: center center;
  
  &.paused {
    animation-play-state: paused;
    
    .orbit-item {
      /* 暂停时也停止反向旋转，保持相对静止 */
      animation-play-state: paused;
    }
  }
}

.orbit-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 1px dashed rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 30px rgba(99, 102, 241, 0.05);
}

/* 轨道上的物体 */
.orbit-item {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  /* 
    1. rotate(--rotate-angle): 将坐标系旋转到对应角度
    2. translate(320px): 将物体沿该角度向外推320px (半径)
    3. rotate(--counter-angle): 将物体本身反向旋转，使其保持水平
  */
  transform: rotate(var(--rotate-angle)) translate(320px) rotate(var(--counter-angle));
  
  /* 为了抵消父容器orbit-ring的旋转，使卡片始终保持水平 */
  animation: counter-rotate 60s linear infinite;
}

.planet-card {
  position: absolute;
  transform: translate(-50%, -50%); /* 居中定位点 */
  width: 120px;
  height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  
  &:hover {
    transform: translate(-50%, -50%) scale(1.2);
    z-index: 20;
    
    .planet-icon {
      box-shadow: 0 0 25px currentColor;
      background: rgba(30, 41, 59, 0.9);
    }
    
    .planet-info h3 {
      color: #fff;
      text-shadow: 0 0 10px currentColor;
      opacity: 1;
    }
  }
}

.planet-icon {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 34px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  margin-bottom: 8px;
  
  /* Icon Variants */
  &.ai-icon { color: #a78bfa; border-color: rgba(139, 92, 246, 0.3); }
  &.case-icon { color: #34d399; border-color: rgba(16, 185, 129, 0.3); }
  &.api-icon { color: #60a5fa; border-color: rgba(59, 130, 246, 0.3); }
  &.ui-icon { color: #fbbf24; border-color: rgba(245, 158, 11, 0.3); }
  &.data-icon { color: #f472b6; border-color: rgba(236, 72, 153, 0.3); }
  &.performance-icon { color: #f87171; border-color: rgba(239, 68, 68, 0.3); }
  &.midscene-icon { color: #818cf8; border-color: rgba(99, 102, 241, 0.3); }
  &.security-icon { color: #f97316; border-color: rgba(249, 115, 22, 0.3); }
  &.knowledge-icon { color: #22c55e; border-color: rgba(34, 197, 94, 0.3); }
  &.assistant-icon { color: #fb923c; border-color: rgba(249, 115, 22, 0.3); }
  &.config-icon { color: #94a3b8; border-color: rgba(100, 116, 139, 0.3); }
  &.system-icon { color: #cbd5e1; border-color: rgba(71, 85, 105, 0.3); }
}

.planet-info {
  h3 {
    font-size: 14px;
    font-weight: 500;
    color: #cbd5e1;
    margin: 0;
    white-space: nowrap;
    transition: all 0.3s;
    text-shadow: 0 2px 4px rgba(0,0,0,0.5);
  }
}

.footer-tips {
  position: absolute;
  bottom: 40px;
  color: rgba(255, 255, 255, 0.3);
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

@keyframes orbit-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 
  反向旋转动画：
  为了让图标始终保持水平（不随轨道倒立），
  我们需要抵消父容器的旋转。
  但是父容器的旋转是动态的，而我们在transform里已经用了一个静态的rotate(var(--counter-angle))来设定初始角度。
  
  正确的做法是：
  1. 静态布局时，item 旋转 angle, translate radius, 然后 rotate -angle。此时item是水平的。
  2. 动画时，Parent 旋转 0 -> 360。
  3. Item 必须额外旋转 0 -> -360 以抵消 Parent 的旋转。
  
  所以动画应该是从 rotate(var(--counter-angle)) 到 rotate(var(--counter-angle) - 360deg)
*/
@keyframes counter-rotate {
  from { transform: rotate(var(--rotate-angle)) translate(320px) rotate(var(--counter-angle)); }
  to { transform: rotate(calc(var(--rotate-angle) + 360deg)) translate(320px) rotate(calc(var(--counter-angle) - 360deg)); }
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.1); opacity: 0.8; }
  100% { transform: scale(1); opacity: 0.5; }
}
</style>
