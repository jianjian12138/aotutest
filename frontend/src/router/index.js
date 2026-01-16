import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

// 静态导入常用组件来避免动态导入问题
import Login from '@/views/auth/Login.vue'
import Register from '@/views/auth/Register.vue'
import Layout from '@/layout/index.vue'
import ProjectList from '@/views/projects/ProjectList.vue'

const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresGuest: true }
  },
  {
    path: '/ai-generation/assistant',
    name: 'Assistant',
    component: () => import('@/views/assistant/AssistantView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/ai-generation',
    component: Layout,
    meta: { requiresAuth: true, title: '用例管理' },
    children: [
      {
        path: '',
        redirect: 'requirement-analysis'
      },
      {
        path: 'requirement-analysis',
        name: 'RequirementAnalysis',
        component: () => import('@/views/requirement-analysis/RequirementAnalysisView.vue'),
        meta: { title: 'AI用例生成' }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: ProjectList,
        meta: { title: '项目管理' }
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('@/views/projects/ProjectDetail.vue')
      },
      {
        path: 'testcases',
        name: 'TestCases',
        component: () => import('@/views/testcases/TestCaseList.vue')
      },
      {
        path: 'testcases/create',
        name: 'CreateTestCase',
        component: () => import('@/views/testcases/TestCaseForm.vue')
      },
      {
        path: 'testcases/:id',
        name: 'TestCaseDetail',
        component: () => import('@/views/testcases/TestCaseDetail.vue')
      },
      {
        path: 'testcases/:id/edit',
        name: 'EditTestCase',
        component: () => import('@/views/testcases/TestCaseEdit.vue')
      },
      {
        path: 'versions',
        name: 'Versions',
        component: () => import('@/views/versions/VersionList.vue')
      },
      {
        path: 'reviews',
        name: 'Reviews',
        component: () => import('@/views/reviews/ReviewList.vue')
      },
      {
        path: 'reviews/create',
        name: 'CreateReview',
        component: () => import('@/views/reviews/ReviewForm.vue')
      },
      {
        path: 'reviews/:id',
        name: 'ReviewDetail',
        component: () => import('@/views/reviews/ReviewDetail.vue')
      },
      {
        path: 'reviews/:id/edit',
        name: 'EditReview',
        component: () => import('@/views/reviews/ReviewForm.vue')
      },
      {
        path: 'review-templates',
        name: 'ReviewTemplates',
        component: () => import('@/views/reviews/ReviewTemplateList.vue')
      },
      {
        path: 'testsuites',
        name: 'TestSuites',
        component: () => import('@/views/testsuites/TestSuiteList.vue')
      },
      {
        path: 'executions',
        name: 'Executions',
        component: () => import('@/views/executions/ExecutionListView.vue')
      },
      {
        path: 'executions/:id',
        name: 'ExecutionDetail',
        component: () => import('@/views/executions/ExecutionDetailView.vue')
      },
      {
        path: 'reports',
        name: 'AiTestReport',
        component: () => import('@/views/reports/AiTestReport.vue')
      },
      {
        path: 'prompt-config',
        name: 'PromptConfig',
        component: () => import('@/views/requirement-analysis/PromptConfig.vue')
      },
      {
        path: 'generated-testcases',
        name: 'GeneratedTestCases',
        component: () => import('@/views/requirement-analysis/GeneratedTestCaseList.vue')
      },
      {
        path: 'task-detail/:taskId',
        name: 'TaskDetail',
        component: () => import('@/views/requirement-analysis/TaskDetail.vue')
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/profile/UserProfile.vue')
      }
    ]
  },
  {
    path: '/api-testing',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: 'dashboard'
      },
      {
        path: 'dashboard',
        name: 'ApiDashboard',
        component: () => import('@/views/api-testing/Dashboard.vue')
      },
      {
        path: 'projects',
        name: 'ApiProjects',
        component: () => import('@/views/api-testing/ProjectManagement.vue')
      },
      {
        path: 'interfaces',
        name: 'ApiInterfaces',
        component: () => import('@/views/api-testing/InterfaceManagement.vue')
      },
      {
        path: 'automation',
        name: 'ApiAutomation',
        component: () => import('@/views/api-testing/AutomationTesting.vue')
      },
      {
        path: 'history',
        name: 'ApiHistory',
        component: () => import('@/views/api-testing/RequestHistory.vue')
      },
      {
        path: 'environments',
        name: 'ApiEnvironments',
        component: () => import('@/views/api-testing/EnvironmentManagement.vue')
      },
      {
        path: 'reports',
        name: 'ApiReports',
        component: () => import('@/views/api-testing/ReportView.vue')
      },
      {
        path: 'scheduled-tasks',
        name: 'ApiScheduledTasks',
        component: () => import('@/views/api-testing/ScheduledTasks.vue')
      },
      {
        path: 'notification-logs',
        name: 'ApiNotificationLogs',
        component: () => import('@/views/notification/NotificationLogs.vue')
      }
    ]
  },
  {
    path: '/ui-automation',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: 'dashboard'
      },
      {
        path: 'dashboard',
        name: 'UiDashboard',
        component: () => import('@/views/ui-automation/dashboard/Dashboard.vue')
      },
      {
        path: 'projects',
        name: 'UiProjects',
        component: () => import('@/views/ui-automation/projects/ProjectList.vue')
      },
      {
        path: 'elements-enhanced',
        name: 'UiElementsEnhanced',
        component: () => import('@/views/ui-automation/elements/ElementManagerEnhanced.vue')
      },
      {
        path: 'test-cases',
        name: 'UiTestCases',
        component: () => import('@/views/ui-automation/test-cases/TestCaseManager.vue')
      },
      {
        path: 'scripts-enhanced',
        name: 'UiScriptsEnhanced',
        component: () => import('@/views/ui-automation/scripts/ScriptEditorEnhanced.vue')
      },
      {
        path: 'scripts',
        name: 'UiScripts',
        component: () => import('@/views/ui-automation/scripts/ScriptList.vue')
      },
      {
        path: 'suites',
        name: 'UiSuites',
        component: () => import('@/views/ui-automation/suites/SuiteList.vue')
      },
      {
        path: 'executions',
        name: 'UiExecutions',
        component: () => import('@/views/ui-automation/executions/ExecutionList.vue')
      },
      {
        path: 'reports',
        name: 'UiReports',
        component: () => import('@/views/ui-automation/reports/ReportList.vue')
      },
      {
        path: 'scheduled-tasks',
        name: 'UiScheduledTasks',
        component: () => import('@/views/ui-automation/scheduled-tasks/ScheduledTasks.vue')
      },
      {
        path: 'notification-logs',
        name: 'UiNotificationLogs',
        component: () => import('@/views/ui-automation/notification/NotificationLogs.vue')
      }
    ]
  },
  {
    path: '/data-factory',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: 'dashboard' },
      { path: 'dashboard', name: 'DataFactoryDashboard', component: () => import('@/views/data-factory/Dashboard.vue') },
      { path: 'sql-generation', name: 'SqlGeneration', component: () => import('@/views/data-factory/SqlGeneration.vue') },
      { path: 'config', name: 'VannaConfig', component: () => import('@/views/data-factory/VannaConfig.vue') },
      { path: 'projects', name: 'ProjectManagement', component: () => import('@/views/data-factory/ProjectManagement.vue') },
      { path: 'saved-queries', name: 'SavedQueries', component: () => import('@/views/data-factory/SavedQueries.vue') },
      { path: 'table-metadata', name: 'TableMetadata', component: () => import('@/views/data-factory/TableMetadata.vue') },
      { path: 'query-history', name: 'QueryHistory', component: () => import('@/views/data-factory/QueryHistory.vue') }
    ]
  },
  {
    path: '/strix-security',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: 'dashboard' },
      { path: 'dashboard', name: 'StrixDashboard', component: () => import('@/views/security/Dashboard.vue') },
      { path: 'scan-tasks', name: 'StrixScanTasks', component: () => import('@/views/security/ScanTasks.vue') },
      { path: 'vulnerabilities', name: 'StrixVulnerabilities', component: () => import('@/views/security/Vulnerabilities.vue') },
      { path: 'reports', name: 'StrixReports', component: () => import('@/views/security/Reports.vue') },
      { path: 'config', name: 'StrixConfig', component: () => import('@/views/security/Config.vue') }
    ]
  },
  {
    path: '/performance-test',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: 'dashboard' },
      { path: 'dashboard', name: 'PerformanceDashboard', component: () => import('@/views/performance-test/Dashboard.vue') },
      { path: 'projects', name: 'PerformanceProjects', component: () => import('@/views/performance-test/ProjectManagement.vue') },
      { path: 'collections', name: 'PerformanceCollections', component: () => import('@/views/performance-test/CollectionManagement.vue') },
      { path: 'requests', name: 'PerformanceRequests', component: () => import('@/views/performance-test/RequestManagement.vue') },
      { path: 'test-suites', name: 'PerformanceTestSuites', component: () => import('@/views/performance-test/TestSuiteManagement.vue') },
      { path: 'executions', name: 'PerformanceExecutions', component: () => import('@/views/performance-test/ExecutionManagement.vue') },
      { path: 'scheduled-tasks', name: 'PerformanceScheduledTasks', component: () => import('@/views/performance-test/ScheduledTaskManagement.vue') }
    ]
  },
  {
    path: '/knowledge-graph',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/knowledge-graph/dashboard' },
      { path: 'dashboard', name: 'KGDashboard', component: () => import('@/views/KnowledgeGraph.vue'), meta: { title: '个人工作台' } },
      { path: 'notebook', name: 'KGNotebook', component: () => import('@/views/KnowledgeGraph.vue'), meta: { title: '个人笔记' } },
      { path: 'idealab', name: 'KGIdeaLab', component: () => import('@/views/KnowledgeGraph.vue'), meta: { title: '深度研究' } },
      { path: 'graph', name: 'KGGraph', component: () => import('@/views/KnowledgeGraph.vue'), meta: { title: '数据库可视化' } },
      { path: 'engine', name: 'KGEngine', component: () => import('@/views/KnowledgeGraph.vue'), meta: { title: 'RAG 管道' } },
      { path: 'sources', name: 'KGSources', component: () => import('@/views/KnowledgeGraph.vue'), meta: { title: '知识库' } },
      { path: 'settings', name: 'KGSettings', component: () => import('@/views/KnowledgeGraph.vue'), meta: { title: '系统设置' } },
      { path: 'evaluator', name: 'KGEvaluator', component: () => import('@/views/KnowledgeGraph.vue'), meta: { title: 'AI 评测师' } }
    ]
  },
  {
    path: '/midscene',
    component: Layout,
    meta: { requiresAuth: true, title: '自然语言Web测试' },
    children: [
      { path: '', redirect: 'dashboard' },
      { path: 'dashboard', name: 'MidsceneDashboard', component: () => import('@/views/midscene/Dashboard.vue'), meta: { title: '数据看板' } },
      { path: 'ai-testing', name: 'MidsceneAITesting', component: () => import('@/views/ui-automation/ai/AITesting.vue'), meta: { title: 'AI智能测试' } },
      { path: 'test-execution', name: 'MidsceneTestExecution', component: () => import('@/views/midscene/TestExecution.vue'), meta: { title: '自然语言测试执行' } },
      { path: 'tasks', name: 'MidsceneTasks', component: () => import('@/views/midscene/TaskManagement.vue'), meta: { title: '任务管理' } },
      { path: 'tasks/:id', name: 'MidsceneTaskDetail', component: () => import('@/views/midscene/TaskDetail.vue'), meta: { title: '任务详情' } },
      { path: 'execution-logs', name: 'MidsceneExecutionLogs', component: () => import('@/views/midscene/ExecutionLogManagement.vue'), meta: { title: '执行日志' } }
    ]
  },
  {
    path: '/wharttest',
    component: Layout,
    meta: { requiresAuth: true, title: '智能化测试' },
    children: [
      { path: '', redirect: 'dashboard' },
      { path: 'dashboard', name: 'WHartTestDashboard', component: () => import('@/views/wharttest/Dashboard.vue') },
      { path: 'llm-chat', name: 'WHartTestLLMChat', component: () => import('@/views/wharttest/LLMChat.vue') },
      { path: 'cases', name: 'WHartTestCaseManagement', component: () => import('@/views/wharttest/CaseManagement.vue') },
      { path: 'projects', name: 'WHartTestProjects', component: () => import('@/views/wharttest/ProjectManagement.vue') },
      { path: 'configs', name: 'WHartTestConfigs', component: () => import('@/views/wharttest/ConfigManagement.vue') },
      { path: 'executions', name: 'WHartTestExecutions', component: () => import('@/views/wharttest/ExecutionManagement.vue') },
      { path: 'tasks', name: 'WHartTestTasks', component: () => import('@/views/wharttest/TaskManagement.vue') },
      { path: 'integration-logs', name: 'WHartTestIntegrationLogs', component: () => import('@/views/wharttest/IntegrationLogManagement.vue') }
    ]
  },
  {
    path: '/configuration',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        component: () => import('@/views/configuration/ConfigurationCenter.vue'),
        children: [
          {
            path: '',
            redirect: 'ai-model'
          },
          {
            path: 'ai-model',
            name: 'ConfigAIModel',
            component: () => import('@/views/requirement-analysis/AIModelConfig.vue'),
            meta: { title: 'AI智能模式配置' }
          },
          {
            path: 'ui-env',
            name: 'ConfigUIEnv',
            component: () => import('@/views/configuration/UIEnvironmentConfig.vue')
          },
          {
            path: 'scheduled-task',
            name: 'ConfigScheduledTask',
            component: () => import('@/views/ui-automation/notification/NotificationConfigs.vue'),
            meta: { title: '定时任务配置' }
          },
          {
            path: 'dify',
            name: 'DifyConfig',
            component: () => import('@/views/configuration/DifyConfig.vue'),
            meta: { title: '工作流配置' }
          },
          {
            path: 'database',
            name: 'DatabaseConfig',
            component: () => import('@/views/configuration/DatabaseConfig.vue'),
            meta: { title: '数据库配置' }
          },
          {
            path: 'users',
            name: 'UserManagement',
            component: () => import('@/views/system/UserManagement.vue')
          }
        ]
      },
      {
        path: 'midscene-config',
        name: 'MidsceneConfig',
        component: () => import('@/views/midscene/ConfigManagement.vue'),
        meta: { title: 'Midscene配置' }
      },
      {
        path: 'cicd-config',
        name: 'CicdConfig',
        component: () => import('@/views/configuration/CicdConfig.vue'),
        meta: { title: 'CI/CD配置' }
      },
      {
        path: 'cicd-dashboard',
        name: 'CICDDashboard',
        component: () => import('@/views/cicd/CICDDashboard.vue'),
        meta: { title: 'CI/CD管理' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/home'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  console.log('路由守卫:', {
    to: to.path,
    from: from.path,
    hasToken: !!userStore.accessToken,
    hasUser: !!userStore.user,
    isAuthenticated: userStore.isAuthenticated
  })

  // 只在应用初始化或从登录页面导航时初始化认证
  if (!userStore.user && userStore.accessToken) {
    try {
      console.log('初始化认证...')
      await userStore.initAuth()
      console.log('认证初始化完成:', {
        hasUser: !!userStore.user,
        isAuthenticated: userStore.isAuthenticated
      })
    } catch (error) {
      console.error('认证初始化失败:', error)
    }
  }

  if (to.meta.requiresAuth && !userStore.isAuthenticated) {
    console.log('需要认证但未认证，跳转到登录页')
    next('/login')
  } else if (to.meta.requiresGuest && userStore.isAuthenticated) {
    console.log('访客页面但已认证，跳转到项目页')
    next('/home')
  } else {
    console.log('路由守卫通过，继续导航')
    next()
  }
})

router.afterEach((to, from) => {
  console.log(`Navigated from ${from.path} to ${to.path}`)
})

export default router