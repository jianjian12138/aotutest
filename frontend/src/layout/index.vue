<template>
  <div class="layout">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="240px">
        <div class="logo" @click="router.push('/home')" style="cursor: pointer;">
          <h2>Testing</h2>
        </div>
        <el-menu
          :default-active="$route.path"
          router
          background-color="#001529"
          text-color="#fff"
          active-text-color="#1890ff"
        >
          <!-- AI用例生成模块菜单 -->
          <template v-if="currentModule === 'ai-generation'">
            <el-sub-menu index="requirement">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                <span>智能用例生成</span>
              </template>
              <el-menu-item index="/ai-generation/requirement-analysis">
                <el-icon><Edit /></el-icon>
                <span>AI用例生成</span>
              </el-menu-item>
              <el-menu-item index="/ai-generation/generated-testcases">
                <el-icon><List /></el-icon>
                <span>AI生成用例记录</span>
              </el-menu-item>
              <el-menu-item index="/ai-generation/prompt-config">
                <el-icon><Setting /></el-icon>
                <span>提示词配置</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/ai-generation/projects">
              <el-icon><Folder /></el-icon>
              <span>项目管理</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/testcases">
              <el-icon><Document /></el-icon>
              <span>测试用例</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/versions">
              <el-icon><Flag /></el-icon>
              <span>版本管理</span>
            </el-menu-item>
            <el-sub-menu index="reviews">
              <template #title>
                <el-icon><Check /></el-icon>
                <span>评审管理</span>
              </template>
              <el-menu-item index="/ai-generation/reviews">
                <el-icon><Document /></el-icon>
                <span>评审列表</span>
              </el-menu-item>
              <el-menu-item index="/ai-generation/review-templates">
                <el-icon><DocumentCopy /></el-icon>
                <span>评审模板</span>
              </el-menu-item>
            </el-sub-menu>

            <el-menu-item index="/ai-generation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>测试计划</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>测试报告</span>
            </el-menu-item>
          </template>

          <!-- 接口测试模块菜单 -->
          <template v-else-if="currentModule === 'api-testing'">
            <el-menu-item index="/api-testing/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>数据看板</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/projects">
              <el-icon><Folder /></el-icon>
              <span>项目管理</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/interfaces">
              <el-icon><Link /></el-icon>
              <span>接口管理</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/automation">
              <el-icon><VideoPlay /></el-icon>
              <span>自动化测试</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/history">
              <el-icon><Timer /></el-icon>
              <span>请求历史</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/environments">
              <span style="margin-right: 8px;">⚙️</span>
              <span>环境管理</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>测试报告</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>定时任务</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>通知列表</span>
            </el-menu-item>
          </template>

          <!-- UI自动化测试模块菜单 -->
          <template v-else-if="currentModule === 'ui-automation'">
            <el-menu-item index="/ui-automation/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>数据看板</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/projects">
              <el-icon><Folder /></el-icon>
              <span>项目管理</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/elements-enhanced">
              <el-icon><Aim /></el-icon>
              <span>元素管理</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/page-objects">
              <el-icon><Collection /></el-icon>
              <span>页面对象</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/test-cases">
              <el-icon><Document /></el-icon>
              <span>用例管理</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scripts-enhanced">
              <el-icon><Edit /></el-icon>
              <span>脚本生成</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scripts">
              <el-icon><DocumentCopy /></el-icon>
              <span>脚本列表</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/suites">
              <el-icon><Collection /></el-icon>
              <span>套件管理</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>执行记录</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>测试报告</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/devices">
              <el-icon><Monitor /></el-icon>
              <span>设备管理</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/debug-files">
              <el-icon><Folder /></el-icon>
              <span>调试文件</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>定时任务</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>通知列表</span>
            </el-menu-item>
          </template>

          <!-- 自然语言测试模块菜单 -->
          <template v-else-if="currentModule === 'natural-language-testing'">
            <el-menu-item index="/natural-language-testing/web-testing">
              <el-icon><Monitor /></el-icon>
              <span>Web 智能测试</span>
            </el-menu-item>
            <el-menu-item index="/natural-language-testing/app-testing">
              <el-icon><Cellphone /></el-icon>
              <span>App 智能测试</span>
            </el-menu-item>
            <el-menu-item index="/natural-language-testing/cases">
              <el-icon><Document /></el-icon>
              <span>智能用例管理</span>
            </el-menu-item>
            <el-menu-item index="/natural-language-testing/execution-records">
              <el-icon><Timer /></el-icon>
              <span>执行历史记录</span>
            </el-menu-item>
          </template>

          <!-- 配置中心模块菜单 -->
          <template v-else-if="currentModule === 'configuration'">
            <el-menu-item index="/configuration/ai-model">
              <el-icon><Cpu /></el-icon>
              <span>AI模型配置</span>
            </el-menu-item>
            <el-menu-item index="/configuration/ui-env">
              <el-icon><Monitor /></el-icon>
              <span>UI环境配置</span>
            </el-menu-item>
            <el-menu-item index="/configuration/cicd">
              <el-icon><Operation /></el-icon>
              <span>CI/CD配置</span>
            </el-menu-item>
            <el-menu-item index="/configuration/database">
              <el-icon><DataLine /></el-icon>
              <span>数据库配置</span>
            </el-menu-item>
            <el-menu-item index="/configuration/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>定时任务</span>
            </el-menu-item>
            <el-menu-item index="/configuration/notifications">
              <el-icon><Bell /></el-icon>
              <span>通知列表</span>
            </el-menu-item>
            <el-menu-item index="/configuration/dify">
              <el-icon><ChatDotRound /></el-icon>
              <span>工作流配置</span>
            </el-menu-item>
            <el-menu-item index="/configuration/users">
              <el-icon><Document /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
          </template>
          
          <!-- 数据工厂模块菜单 -->
          <template v-else-if="currentModule === 'data-factory'">
            <el-menu-item index="/data-factory/dashboard">
              <el-icon><DataBoard /></el-icon>
              <span>数据看板</span>
            </el-menu-item>
            <el-menu-item index="/data-factory/sql-generation">
              <el-icon><ChatDotRound /></el-icon>
              <span>SQL生成</span>
            </el-menu-item>
            <el-menu-item index="/data-factory/config">
              <el-icon><Setting /></el-icon>
              <span>配置管理</span>
            </el-menu-item>
            <el-menu-item index="/data-factory/projects">
              <el-icon><Folder /></el-icon>
              <span>项目管理</span>
            </el-menu-item>
            <el-menu-item index="/data-factory/saved-queries">
              <el-icon><Document /></el-icon>
              <span>保存查询</span>
            </el-menu-item>
            <el-menu-item index="/data-factory/table-metadata">
              <el-icon><DataLine /></el-icon>
              <span>表元数据</span>
            </el-menu-item>
            <el-menu-item index="/data-factory/query-history">
              <el-icon><Timer /></el-icon>
              <span>查询历史</span>
            </el-menu-item>
          </template>
          
          <!-- 性能测试模块菜单 -->
          <template v-else-if="currentModule === 'performance-test'">
            <el-menu-item index="/performance-test/dashboard">
              <el-icon><Timer /></el-icon>
              <span>数据看板</span>
            </el-menu-item>
            <el-menu-item index="/performance-test/projects">
              <el-icon><Folder /></el-icon>
              <span>项目管理</span>
            </el-menu-item>
            <el-menu-item index="/performance-test/collections">
              <el-icon><Collection /></el-icon>
              <span>集合管理</span>
            </el-menu-item>
            <el-menu-item index="/performance-test/requests">
              <el-icon><Link /></el-icon>
              <span>请求管理</span>
            </el-menu-item>
            <el-menu-item index="/performance-test/test-suites">
              <el-icon><List /></el-icon>
              <span>测试套件</span>
            </el-menu-item>
            <el-menu-item index="/performance-test/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>执行管理</span>
            </el-menu-item>
            <el-menu-item index="/performance-test/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>定时任务</span>
            </el-menu-item>
          </template>
          
          <!-- 自然语言Web测试模块菜单 - 已废弃，合并入natural-language-testing -->
          <!-- <template v-else-if="currentModule === 'midscene'">
            <el-menu-item index="/midscene/dashboard">
              <el-icon><Message /></el-icon>
              <span>数据看板</span>
            </el-menu-item>
            <el-menu-item index="/midscene/config">
              <el-icon><Setting /></el-icon>
              <span>配置管理</span>
            </el-menu-item>
            <el-menu-item index="/midscene/tasks">
              <el-icon><Document /></el-icon>
              <span>任务管理</span>
            </el-menu-item>
            <el-menu-item index="/midscene/execution-logs">
              <el-icon><Timer /></el-icon>
              <span>执行日志</span>
            </el-menu-item>
          </template> -->
          
          <!-- 安全测试模块菜单 -->
          <template v-else-if="currentModule === 'strix-security'">
            <el-menu-item index="/strix-security/dashboard">
              <el-icon><Lock /></el-icon>
              <span>数据看板</span>
            </el-menu-item>
            <el-menu-item index="/strix-security/scan-tasks">
              <el-icon><VideoPlay /></el-icon>
              <span>扫描任务</span>
            </el-menu-item>
            <el-menu-item index="/strix-security/vulnerabilities">
              <el-icon><Warning /></el-icon>
              <span>漏洞管理</span>
            </el-menu-item>
            <el-menu-item index="/strix-security/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>测试报告</span>
            </el-menu-item>
            <el-menu-item index="/strix-security/config">
              <el-icon><Setting /></el-icon>
              <span>配置管理</span>
            </el-menu-item>
          </template>
          
          <!-- CI/CD管理模块菜单 -->
          <template v-else-if="currentModule === 'cicd'">
            <el-menu-item index="/cicd/dashboard">
              <el-icon><Operation /></el-icon>
              <span>CI/CD仪表盘</span>
            </el-menu-item>
          </template>
          
          <!-- 知识图谱模块菜单 -->
          <template v-else-if="currentModule === 'knowledge-graph'">
            <el-menu-item index="/knowledge-graph/dashboard">
              <el-icon><Document /></el-icon>
              <span>知识库管理</span>
            </el-menu-item>
            <el-menu-item index="/knowledge-graph/ai-agent">
              <el-icon><Service /></el-icon>
              <span>AI 助手</span>
            </el-menu-item>
            <el-menu-item index="/knowledge-graph/graph-viz">
              <el-icon><Connection /></el-icon>
              <span>图谱可视化</span>
            </el-menu-item>
          </template>
          
          <!-- WHartTest模块菜单 -->
          <template v-else-if="currentModule === 'wharttest'">
            <el-menu-item index="/wharttest/dashboard">
              <el-icon><DataAnalysis /></el-icon>
              <span>数据看板</span>
            </el-menu-item>
            <el-menu-item index="/wharttest/projects">
              <el-icon><Folder /></el-icon>
              <span>项目管理</span>
            </el-menu-item>
            <el-menu-item index="/wharttest/configs">
              <el-icon><Setting /></el-icon>
              <span>配置管理</span>
            </el-menu-item>
            <el-menu-item index="/wharttest/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>执行管理</span>
            </el-menu-item>
            <el-menu-item index="/wharttest/tasks">
              <el-icon><Document /></el-icon>
              <span>任务管理</span>
            </el-menu-item>
            <el-menu-item index="/wharttest/integration-logs">
              <el-icon><Timer /></el-icon>
              <span>集成日志</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-aside>

      <!-- 主体内容 -->
      <el-container>
        <!-- 顶部导航 -->
        <el-header height="60px">
          <div class="header-content">
            <div class="header-left">
              <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/home' }">首页</el-breadcrumb-item>
                <el-breadcrumb-item v-if="moduleName">{{ moduleName }}</el-breadcrumb-item>
                <el-breadcrumb-item>{{ breadcrumbTitle }}</el-breadcrumb-item>
              </el-breadcrumb>
            </div>
            <div class="header-right">
              <el-dropdown @command="handleCommand">
                <span class="user-info">
                  <el-avatar :size="32" :src="userStore.user?.avatar" />
                  <span class="username">{{ userStore.user?.username }}</span>
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="profile">个人设置</el-dropdown-item>
                    <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </el-header>

        <!-- 页面内容 -->
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import {
  Monitor, Folder, Document, Flag, Check, Collection, VideoPlay,
  DataAnalysis, ChatDotRound, DocumentCopy, Link, MagicStick,
  Odometer, Timer, Setting, AlarmClock, Bell, Aim, Edit, Cpu,
  DataBoard, DataLine, Message, Lock, ArrowDown, Warning, List,
  Operation, Cellphone
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const currentModule = computed(() => {
  console.log('Current route:', route.path)
  if (route.path.startsWith('/ai-generation')) return 'ai-generation'
  if (route.path.startsWith('/api-testing')) {
    console.log('API Testing module detected')
    return 'api-testing'
  }
  if (route.path.startsWith('/ui-automation')) {
    console.log('Detected UI Automation module');
    return 'ui-automation';
  }
  if (route.path.startsWith('/natural-language-testing')) return 'natural-language-testing'
  if (route.path.startsWith('/configuration')) return 'configuration'
  if (route.path.startsWith('/data-factory')) return 'data-factory'
  if (route.path.startsWith('/performance-test')) return 'performance-test'
  if (route.path.startsWith('/midscene')) return 'midscene'
  if (route.path.startsWith('/strix-security')) return 'strix-security'
  if (route.path.startsWith('/cicd')) return 'cicd'
  if (route.path.startsWith('/knowledge-graph')) return 'knowledge-graph'
  if (route.path.startsWith('/wharttest')) return 'wharttest'
  return ''
})

const moduleName = computed(() => {
  const map = {
    'ai-generation': '用例管理',
    'api-testing': '接口测试',
    'ui-automation': 'UI测试',
    'natural-language-testing': '自然语言测试',
    'configuration': '配置中心',
    'data-factory': '数据工厂',
    'performance-test': '性能测试',
    'midscene': '自然语言测试',
    'strix-security': '安全测试',
    'cicd': 'CI/CD管理',
    'knowledge-graph': '知识图谱',
    'wharttest': '智能化测试'
  }
  return map[currentModule.value] || ''
})

const breadcrumbTitle = computed(() => {
  const routeMap = {
    // 用例管理
    '/ai-generation/requirement-analysis': 'AI用例生成',
    '/ai-generation/generated-testcases': 'AI生成用例记录',
    '/ai-generation/prompt-config': '提示词配置',
    '/ai-generation/projects': '项目管理',
    '/ai-generation/testcases': '测试用例',
    '/ai-generation/versions': '版本管理',
    '/ai-generation/reviews': '评审列表',
    '/ai-generation/review-templates': '评审模板',
    '/ai-generation/testsuites': '测试套件',
    '/ai-generation/executions': '测试计划',
    '/ai-generation/reports': '测试报告',
    
    // 接口测试
    '/api-testing/dashboard': '数据看板',
    '/api-testing/projects': '项目管理',
    '/api-testing/interfaces': '接口管理',
    '/api-testing/automation': '自动化测试',
    '/api-testing/history': '请求历史',
    '/api-testing/environments': '环境管理',
    '/api-testing/reports': '测试报告',
    '/api-testing/scheduled-tasks': '定时任务',
    '/api-testing/notification-logs': '通知列表',
    
    // UI测试
    '/ui-automation/dashboard': '数据看板',
    '/ui-automation/projects': '项目管理',
    '/ui-automation/elements-enhanced': '元素管理',
    '/ui-automation/page-objects': '页面对象',
    '/ui-automation/test-cases': '用例管理',
    '/ui-automation/scripts-enhanced': '脚本生成',
    '/ui-automation/scripts': '脚本列表',
    '/ui-automation/suites': '套件管理',
    '/ui-automation/executions': '执行记录',
    '/ui-automation/reports': '测试报告',
    '/ui-automation/devices': '设备管理',
    '/ui-automation/debug-files': '调试文件',
    '/ui-automation/scheduled-tasks': '定时任务',
    '/ui-automation/notification-logs': '通知列表',
    
    // 自然语言测试 (AI 智能模式升级)
    '/natural-language-testing/web-testing': 'Web 智能测试',
    '/natural-language-testing/app-testing': 'App 智能测试',
    '/natural-language-testing/cases': '智能用例管理',
    '/natural-language-testing/execution-records': '执行历史记录',

    // 配置中心
    '/configuration/ai-model': 'AI模型配置',
    '/configuration/ui-env': 'UI环境配置',
    '/configuration/cicd': 'CI/CD配置',
    '/configuration/database': '数据库配置',
    '/configuration/scheduled-tasks': '定时任务',
    '/configuration/notifications': '通知列表',
    '/configuration/dify': '工作流配置',
    
    // 数据工厂
    '/data-factory/dashboard': '数据看板',
    '/data-factory/sql-generation': 'SQL生成',
    '/data-factory/config': '配置管理',
    '/data-factory/projects': '项目管理',
    '/data-factory/saved-queries': '保存查询',
    '/data-factory/table-metadata': '表元数据',
    '/data-factory/query-history': '查询历史',
    
    // 性能测试
    '/performance-test/dashboard': '数据看板',
    '/performance-test/projects': '项目管理',
    '/performance-test/collections': '集合管理',
    '/performance-test/requests': '请求管理',
    '/performance-test/test-suites': '测试套件',
    '/performance-test/executions': '执行管理',
    '/performance-test/scheduled-tasks': '定时任务',
    
    // 自然语言测试
    '/midscene/dashboard': '数据看板',
    '/midscene/config': '配置管理',
    '/midscene/tasks': '任务管理',
    '/midscene/tasks/:id': '任务详情',
    '/midscene/execution-logs': '执行日志',
    
    // 安全测试
    '/strix-security/dashboard': '数据看板',
    '/strix-security/scan-tasks': '扫描任务',
    '/strix-security/vulnerabilities': '漏洞管理',
    '/strix-security/reports': '测试报告',
    '/strix-security/config': '配置管理',
    
    // CI/CD管理
    '/cicd/dashboard': 'CI/CD仪表盘',
    
    // 知识图谱
    '/knowledge-graph': '知识图谱',
    
    // WHartTest
    '/wharttest/dashboard': '数据看板',
    '/wharttest/projects': '项目管理',
    '/wharttest/configs': '配置管理',
    '/wharttest/executions': '执行管理',
    '/wharttest/tasks': '任务管理',
    '/wharttest/integration-logs': '集成日志',
    
    // 配置中心
    '/configuration/users': '用户管理',
    
    '/profile': '个人设置'
  }
  return routeMap[route.path] || route.meta.title || ''
})

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    ElMessage.success('退出登录成功')
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/configuration/users')
  }
}
</script>

<style lang="scss" scoped>
.layout {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.layout > .el-container {
  height: 100%;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #001529;
  color: white;
  border-bottom: 1px solid #1f1f1f;
  flex-shrink: 0;

  h2 {
    margin: 0;
    font-weight: 600;
  }
}

.el-aside {
  background-color: #001529;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .el-menu {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    border-right: none;
    
    &::-webkit-scrollbar {
      width: 0; /* 隐藏侧边栏滚动条但保留功能 */
    }
    
    .icon {
      margin-right: 8px;
      font-size: 18px;
    }
    
    /* 确保所有菜单项的图标都能显示 */
    .el-menu-item {
      display: flex;
      align-items: center;
      
      .el-icon {
        display: inline-block;
        margin-right: 8px;
        width: 18px;
        height: 18px;
        vertical-align: middle;
      }
    }
    
    /* 针对环境管理菜单项的特殊样式 */
    .el-menu-item:nth-child(6) {
      .el-icon {
        display: inline-block !important;
        visibility: visible !important;
      }
    }
  }
}

/* 内部容器 (Header + Main) */
.el-container .el-container {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.el-header {
  background-color: white;
  border-bottom: 1px solid #e8e8e8;
  padding: 0;
  flex-shrink: 0;

  .header-content {
    height: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 20px;
  }

  .user-info {
    display: flex;
    align-items: center;
    cursor: pointer;

    .username {
      margin: 0 8px;
      color: #303133;
    }
  }
}

.el-main {
  background-color: #f5f5f5;
  padding: 20px;
  flex: 1;
  overflow-y: auto; /* 内容区域独立滚动 */
  overflow-x: hidden;
}
</style>
