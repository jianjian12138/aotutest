import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

// 静态导入常用组件来避免动态导入问题
import Login from '@/views/auth/Login.vue'
import Register from '@/views/auth/Register.vue'
import Layout from '@/layout/index.vue'

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
    path: '/agent-workspace',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'AgentWorkspace',
        component: () => import('@/views/agent/AgentWorkspace.vue')
      }
    ]
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
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: 'requirement-analysis'
      },
      {
        path: 'requirements',
        name: 'RequirementList',
        component: () => import('@/views/requirement-analysis/RequirementDocumentList.vue')
      },
      {
        path: 'requirement-analysis',
        name: 'RequirementAnalysis',
        component: () => import('@/views/requirement-analysis/RequirementAnalysisView.vue')
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
        path: 'interfaces',
        name: 'ApiInterfaces',
        component: () => import('@/views/api-testing/InterfaceManagement.vue')
      },
      {
        path: 'test-cases',
        name: 'ApiTestCases',
        component: () => import('@/views/api-testing/TestCaseManagement.vue')
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
        path: 'elements-enhanced',
        name: 'UiElementsEnhanced',
        component: () => import('@/views/ui-automation/elements/ElementManagerEnhanced.vue')
      },
      {
        path: 'page-objects',
        name: 'UiPageObjects',
        component: () => import('@/views/ui-automation/page-objects/PageObjectManager.vue')
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
        path: 'scripts/editor',
        name: 'UiScriptEditor',
        component: () => import('@/views/ui-automation/scripts/ScriptEditorEnhanced.vue')
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
        path: 'devices',
        name: 'UiDevices',
        component: () => import('@/views/ui-automation/device/DeviceManagement.vue')
      },
      {
        path: 'agents',
        name: 'UiAgents',
        component: () => import('@/views/ui-automation/agent/AgentManagement.vue')
      },
          {
            path: 'debug-files',
            name: 'UiDebugFiles',
            component: () => import('@/views/ui-automation/debug/DebugFileManager.vue')
          },
          {
            path: 'reports',
            name: 'UiReports',
            component: () => import('@/views/ui-automation/reports/ReportList.vue')
          }
    ]
  },
  {
    path: '/natural-language-testing',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: 'web-testing'
      },
      {
        path: 'web-testing',
        name: 'WebAITesting',
        component: () => import('@/views/ui-automation/ai/MobileAITesting.vue')
      },
      {
        path: 'app-testing',
        name: 'MobileAITesting',
        component: () => import('@/views/ui-automation/ai/MobileAITesting.vue')
      },
      {
        path: 'inspector',
        name: 'SmartInspector',
        component: () => import('@/views/ui-automation/ai/SmartInspector.vue')
      },
      {
        path: 'api-testing',
        name: 'ApiAITesting',
        component: () => import('@/views/ui-automation/ai/ApiAITesting.vue'),
        meta: { mode: 'api' }
      },
      {
        path: 'cases',
        name: 'AICaseList',
        component: () => import('@/views/ui-automation/ai/AICaseList.vue')
      },
      {
        path: 'execution-records',
        name: 'AIExecutionRecords',
        component: () => import('@/views/ui-automation/ai/AIExecutionRecords.vue')
      },
      {
        path: 'agent-browser',
        name: 'AgentBrowser',
        component: () => import('@/views/ui-automation/ai/AgentBrowser.vue')
      }
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
            component: () => import('@/views/requirement-analysis/AIModelConfig.vue')
          },
          {
            path: 'ui-env',
            name: 'ConfigUIEnv',
            component: () => import('@/views/configuration/UIEnvironmentConfig.vue')
          },
          {
            path: 'ai-mode',
            name: 'ConfigAIMode',
            component: () => import('@/views/configuration/AIIntelligentModeConfig.vue')
          },

          {
            path: 'cicd',
            component: () => import('@/views/configuration/ConfigurationCenter.vue'), // Reuse the simple router-view wrapper
            children: [
              {
                path: '',
                redirect: 'pipelines'
              },
              {
                path: 'pipelines',
                name: 'PipelineList',
                component: () => import('@/views/cicd/PipelineList.vue')
              },
              {
                path: 'pipelines/:id',
                name: 'PipelineDetail',
                component: () => import('@/views/cicd/PipelineDetail.vue')
              }
            ]
          },
          {
            path: 'database',
            name: 'ConfigDatabase',
            component: () => import('@/views/configuration/DatabaseConfig.vue')
          },

          {
            path: 'dify',
            name: 'DifyConfig',
            component: () => import('@/views/configuration/DifyConfig.vue')
          },
          {
            path: 'mcp',
            name: 'MCPConfig',
            component: () => import('@/views/configuration/MCPConfig.vue')
          },
          {
            path: 'skills',
            name: 'SkillsConfig',
            component: () => import('@/views/configuration/SkillsConfig.vue')
          },
          {
            path: 'agent-profiles',
            name: 'AgentProfileConfig',
            component: () => import('@/views/configuration/AgentProfileConfig.vue')
          },
          {
            path: 'agent-skills',
            name: 'AgentSkillConfig',
            component: () => import('@/views/configuration/AgentSkillConfig.vue')
          },
          {
            path: 'users',
            name: 'UserManagement',
            component: () => import('@/views/system/UserManagement.vue')
          },
          {
            path: 'parameters',
            name: 'ParameterManagement',
            component: () => import('@/views/configuration/ParameterManagement.vue')
          },
          {
            path: 'common-methods',
            name: 'CommonMethodManagement',
            component: () => import('@/views/configuration/CommonMethodManagement.vue')
          }
        ]
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

      { path: 'saved-queries', name: 'SavedQueries', component: () => import('@/views/data-factory/SavedQueries.vue') },
      { path: 'table-metadata', name: 'TableMetadata', component: () => import('@/views/data-factory/TableMetadata.vue') },
      { path: 'query-history', name: 'QueryHistory', component: () => import('@/views/data-factory/QueryHistory.vue') },
      { path: 'data-generator', name: 'TestDataGenerator', component: () => import('@/views/data-factory/TestDataGenerator.vue') }
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

      { path: 'config', name: 'StrixConfig', component: () => import('@/views/security/Config.vue') }
    ]
  },
  {
    path: '/special-testing',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: 'dashboard'
      },
      {
        path: 'dashboard',
        name: 'SpecialTestingDashboard',
        component: () => import('@/views/special-testing/Dashboard.vue')
      },
      {
        path: 'mqtt',
        name: 'MqttTest',
        component: () => import('@/views/special-testing/mqtt/MqttTest.vue')
      },
      {
        path: 'monkey',
        name: 'MonkeyTest',
        component: () => import('@/views/special-testing/monkey/MonkeyTest.vue')
      },
      {
        path: 'redis',
        name: 'RedisTest',
        component: () => import('@/views/special-testing/middleware/RedisTest.vue')
      },
      {
        path: 'kafka',
        name: 'KafkaTest',
        component: () => import('@/views/special-testing/middleware/KafkaTest.vue')
      }
    ]
  },
  {
    path: '/performance-test',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: 'dashboard' },
      { path: 'dashboard', name: 'PerformanceDashboard', component: () => import('@/views/performance-test/Dashboard.vue') },

      { path: 'collections', name: 'PerformanceCollections', component: () => import('@/views/performance-test/CollectionManagement.vue') },
      { path: 'requests', name: 'PerformanceRequests', component: () => import('@/views/performance-test/RequestManagement.vue') },
      { path: 'test-suites', name: 'PerformanceTestSuites', component: () => import('@/views/performance-test/TestSuiteManagement.vue') },
      { path: 'executions', name: 'PerformanceExecutions', component: () => import('@/views/performance-test/ExecutionManagement.vue') },
      { path: 'executions/:id/report', name: 'PerformanceExecutionReport', component: () => import('@/views/performance-test/ExecutionReport.vue') },

    ]
  },
  {
    path: '/unified',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: 'projects'
      },

      {
        path: 'projects',
        name: 'UnifiedProjects',
        component: () => import('@/views/unified/projects/ProjectList.vue')
      },
      {
        path: 'projects/:id',
        name: 'UnifiedProjectDetail',
        component: () => import('@/views/unified/projects/ProjectDetail.vue')
      },

      {
        path: 'scheduler',
        name: 'UnifiedScheduler',
        component: () => import('@/views/unified/scheduler/TaskList.vue')
      },
      {
        path: 'scheduler/:id',
        name: 'UnifiedTaskDetail',
        component: () => import('@/views/unified/scheduler/TaskDetail.vue')
      },
      {
        path: 'notifications',
        name: 'UnifiedNotifications',
        component: () => import('@/views/unified/notifications/ConfigList.vue')
      },
      {
        path: 'reports',
        name: 'UnifiedReports',
        component: () => import('@/views/unified/reports/ReportList.vue')
      },
      {
        path: 'reports/:id',
        name: 'UnifiedReportDetail',
        component: () => import('@/views/unified/reports/ReportDetail.vue')
      }
    ]
  },
  {
    path: '/knowledge-graph',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        component: () => import('@/views/knowledge-graph/KnowledgeGraph.vue'),
        children: [
          {
            path: '',
            redirect: 'dashboard'
          },
          {
            path: 'dashboard',
            name: 'KGDashboard',
            component: () => import('@/views/knowledge-graph/components/KnowledgeBase.vue')
          },
          {
            path: 'ai-agent',
            name: 'KGAIAgent',
            component: () => import('@/views/knowledge-graph/components/AIAgent.vue')
          }
        ]
      }
    ]
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
