<template>
  <div class="home-container" @mousemove="handleGlobalMouseMove" @mouseup="handleGlobalMouseUp">
    <!-- 极简星空背景 -->
    <div class="space-background">
      <div v-for="n in 80" :key="n" class="star" :style="getStarStyle(n)"></div>
      <div class="ambient-glow"></div>
    </div>

    <!-- 用户信息 -->
    <div class="home-user-bar" v-if="userStore.user">
      <el-dropdown placement="bottom-end">
        <span class="user-trigger">
          <div class="avatar-circle">{{ avatarInitials }}</div>
          <span class="username">{{ displayName }}</span>
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="router.push('/profile')">个人中心</el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div class="main-scene">
      <!-- 极简核心 -->
      <div class="center-module">
        <div class="module-glow"></div>
        <div class="module-content">
          <div class="brand-title">
            <span class="main">TESTING</span>
            <span class="sub">PLATFORM</span>
          </div>
          <div class="divider"></div>
          <p class="tagline">智能测试一体化平台</p>
        </div>
        <div class="orbit-path"></div>
      </div>

      <!-- 旋转轨道 -->
      <div
        class="planet-orbit"
        :class="{ paused: isPaused || activeDragIndex !== null }"
      >
        <div
          v-for="(card, index) in cards"
          :key="card.type"
          class="planet-anchor"
          :style="getItemStyle(index)"
        >
          <div class="planet-rotator">
            <div 
              class="planet-card" 
              :class="{ 'is-dragging': activeDragIndex === index }"
              @click="handleCardClick(card)"
              @mousedown="handleMouseDown($event, index)"
              :style="getCardDynamicStyle(index)"
            >
              <div class="icon-section" :style="`--p-color: ${card.color}`">
                <el-icon><component :is="card.icon" /></el-icon>
              </div>
              <div class="label-section">
                <span>{{ card.title }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="footer-hint">
      <el-icon class="ani-mouse"><Mouse /></el-icon>
      <span>按住模块可任意拖拽，释放后自动回弹</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  MagicStick, Link, Monitor, DataAnalysis, Cpu, Setting, DocumentChecked,
  Operation, ArrowDown, Tools, Folder, Mouse
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const isPaused = ref(false)

// 拖拽相关状态
const activeDragIndex = ref(null)
const mouseStartPos = { x: 0, y: 0 }
const initialOffsets = { x: 0, y: 0 }
const dragDistance = ref(0) // 用于区分点击和拖放

const cards = ref([
  { type: 'case', title: '需求与用例', icon: DocumentChecked, color: '#10b981', offsetX: 0, offsetY: 0 },
  { type: 'api', title: '接口测试', icon: Link, color: '#3b82f6', offsetX: 0, offsetY: 0 },
  { type: 'ui', title: 'UI自动化', icon: Monitor, color: '#f59e0b', offsetX: 0, offsetY: 0 },
  { type: 'midscene', title: '智能化测试', icon: Operation, color: '#6366f1', offsetX: 0, offsetY: 0 },
  { type: 'security', title: '安全测试', icon: Cpu, color: '#f97316', offsetX: 0, offsetY: 0 },
  { type: 'knowledge', title: '知识图谱', icon: MagicStick, color: '#22c55e', offsetX: 0, offsetY: 0 },
  { type: 'special', title: '专项测试', icon: Tools, color: '#ef4444', offsetX: 0, offsetY: 0 },
  { type: 'data', title: '数据工厂', icon: DataLine, color: '#ec4899', offsetX: 0, offsetY: 0 },
  { type: 'performance', title: '性能测试', icon: Cpu, color: '#8b5cf6', offsetX: 0, offsetY: 0 },
  { type: 'config', title: '配置中心', icon: Setting, color: '#64748b', offsetX: 0, offsetY: 0 },
  { type: 'unified', title: '统一管理', icon: Folder, color: '#a855f7', offsetX: 0, offsetY: 0 },
  { type: 'eval', title: 'Agent 测评', icon: DataAnalysis, color: '#0ea5e9', offsetX: 0, offsetY: 0 }
])

const totalItems = cards.value.length

// 获取星星样式
const getStarStyle = (n) => ({
  width: `${Math.random() * 2 + 1}px`,
  height: `${Math.random() * 2 + 1}px`,
  left: `${Math.random() * 100}%`,
  top: `${Math.random() * 100}%`,
  opacity: Math.random() * 0.7 + 0.3,
  '--d': `${2 + Math.random() * 4}s`
})

// 获取位置锚点样式
const getItemStyle = (index) => {
  const angle = (360 / totalItems) * index
  return {
    '--start-angle': `${angle}deg`,
    '--counter-angle': `-${angle}deg`
  }
}

// 获取卡片动态样式 (偏移)
const getCardDynamicStyle = (index) => {
  const card = cards.value[index]
  return {
    transform: `translate(calc(-50% + ${card.offsetX}px), calc(-50% + ${card.offsetY}px))`
  }
}

// 拖拽逻辑
const handleMouseDown = (e, index) => {
  activeDragIndex.value = index
  mouseStartPos.x = e.clientX
  mouseStartPos.y = e.clientY
  initialOffsets.x = cards.value[index].offsetX
  initialOffsets.y = cards.value[index].offsetY
  dragDistance.value = 0
  
  // 防止文本选中
  e.preventDefault()
}

const handleGlobalMouseMove = (e) => {
  if (activeDragIndex.value === null) return
  
  const dx = e.clientX - mouseStartPos.x
  const dy = e.clientY - mouseStartPos.y
  dragDistance.value += Math.sqrt(dx*dx + dy*dy)
  
  cards.value[activeDragIndex.value].offsetX = initialOffsets.x + dx
  cards.value[activeDragIndex.value].offsetY = initialOffsets.y + dy
}

const handleGlobalMouseUp = () => {
  if (activeDragIndex.value === null) return
  
  const index = activeDragIndex.value
  cards.value[index].offsetX = 0
  cards.value[index].offsetY = 0
  
  setTimeout(() => {
    activeDragIndex.value = null
  }, 10)
}

const handleCardClick = (card) => {
  if (dragDistance.value < 10) {
    handleNavigate(card.type)
  }
}

const avatarInitials = computed(() => {
  const u = userStore.user
  return u ? (u.username || u.email || '').slice(0, 2).toUpperCase() : 'AD'
})

const displayName = computed(() => {
  return userStore.user?.username || '管理员'
})

const handleLogout = async () => {
  await userStore.logout()
  router.push('/login')
}

const handleNavigate = (type) => {
  const routes = {
    case: '/ai-generation/requirements',
    api: '/api-testing/dashboard',
    ui: '/ui-automation/dashboard',
    midscene: '/natural-language-testing/web-testing',
    security: '/strix-security/dashboard',
    knowledge: '/knowledge-graph/dashboard',
    special: '/special-testing/dashboard',
    data: '/data-factory/dashboard',
    performance: '/performance-test/dashboard',
    config: '/configuration/ai-model',
    unified: '/unified/projects',
    eval: '/eval'
  }
  if (routes[type]) router.push(routes[type])
}
</script>

<style lang="scss" scoped>
.home-container {
  height: 100vh;
  width: 100%;
  background: radial-gradient(circle at center, #1e293b 0%, #020617 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  position: relative;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

.space-background {
  position: absolute;
  inset: 0;
  .star {
    position: absolute;
    background: #fff;
    border-radius: 50%;
    animation: twinkle var(--d) infinite ease-in-out;
  }
  .ambient-glow {
    position: absolute;
    width: 60%;
    height: 60%;
    top: 20%; left: 20%;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.05), transparent 70%);
  }
}

.home-user-bar {
  position: absolute;
  top: 32px; right: 48px;
  z-index: 100;
  .user-trigger {
    display: flex; align-items: center; gap: 12px;
    padding: 6px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 100px;
    color: #e2e8f0;
    cursor: pointer;
    backdrop-filter: blur(10px);
    &:hover { background: rgba(255, 255, 255, 0.1); }
  }
  .avatar-circle {
    width: 28px; height: 28px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700;
  }
}

.main-scene {
  position: relative;
  width: 1000px; height: 1000px;
  display: flex; justify-content: center; align-items: center;
}

.center-module {
  position: absolute;
  width: 280px; height: 280px;
  z-index: 5;
  display: flex; flex-direction: column; justify-content: center; align-items: center;
  text-align: center;

  .module-glow {
    position: absolute;
    width: 140%; height: 140%;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.15), transparent 70%);
    animation: pulse 4s infinite;
  }

  .brand-title {
    display: flex; flex-direction: column;
    span.main { font-size: 42px; font-weight: 900; letter-spacing: 2px; color: #fff; line-height: 1; }
    span.sub { font-size: 24px; font-weight: 300; letter-spacing: 8px; color: #94a3b8; margin-top: 4px; }
  }

  .divider {
    width: 40px; height: 2px;
    background: #6366f1;
    margin: 24px 0;
  }

  .tagline {
    color: #64748b; font-size: 14px; letter-spacing: 4px; text-transform: uppercase;
  }

  .orbit-path {
    position: absolute;
    width: 840px; height: 840px; /* 2 * radius */
    border: 1px solid rgba(255, 255, 255, 0.03);
    border-radius: 50%;
    pointer-events: none;
  }
}

.planet-orbit {
  position: absolute;
  width: 100%; height: 100%;
  animation: rotate-orbit 120s linear infinite;
  &.paused { animation-play-state: paused; }
}

.planet-anchor {
  position: absolute;
  top: 50%; left: 50%;
  transform: rotate(var(--start-angle)) translate(420px);
}

.planet-rotator {
  position: absolute;
  width: 0; height: 0;
  animation: counter-rotate-item 120s linear infinite;
  
  .paused & { animation-play-state: paused; }
}

.planet-card {
  position: absolute;
  /* 核心：使用 transition 处理回弹效果 */
  transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
  display: flex; flex-direction: column; align-items: center;
  padding: 16px;
  cursor: grab;
  user-select: none;
  z-index: 10;
  
  &:active { cursor: grabbing; }

  &.is-dragging {
    /* 拖拽时禁用 transition 以获得即时反馈 */
    transition: none;
    cursor: grabbing;
    z-index: 100;
    .icon-section {
      transform: scale(1.1);
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), 0 0 30px var(--p-color);
      border-color: var(--p-color);
    }
  }

  .icon-section {
    width: 64px; height: 64px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    display: flex; align-items: center; justify-content: center;
    font-size: 28px;
    color: var(--p-color);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
  }

  .label-section {
    margin-top: 12px;
    opacity: 0.7;
    transition: all 0.3s;
    span {
      font-size: 14px; font-weight: 500; color: #f1f5f9;
      white-space: nowrap;
    }
  }

  &:hover:not(.is-dragging) {
    transform: translate(-50%, -60%) scale(1.1) rotate(var(--counter-angle));
    .icon-section {
      background: rgba(30, 41, 59, 0.9);
      border-color: var(--p-color);
      box-shadow: 0 0 30px rgba(var(--p-color), 0.3);
      transform: translateY(-5px);
    }
    .label-section { opacity: 1; transform: translateY(2px); text-shadow: 0 0 10px rgba(255,255,255,0.5); }
  }
}

.footer-hint {
  position: absolute;
  bottom: 48px;
  color: #475569;
  font-size: 13px;
  display: flex; align-items: center; gap: 10px;
  .ani-mouse { animation: mouse-float 2s infinite; }
}

@keyframes rotate-orbit { from { transform: rotate(0); } to { transform: rotate(360deg); } }
@keyframes counter-rotate-item {
  from { transform: translate(-50%, -50%) rotate(var(--counter-angle)); }
  to { transform: translate(-50%, -50%) rotate(calc(var(--counter-angle) - 360deg)); }
}
@keyframes pulse { 0%, 100% { opacity: 0.5; transform: scale(1); } 50% { opacity: 1; transform: scale(1.1); } }
@keyframes twinkle { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
@keyframes mouse-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
</style>
