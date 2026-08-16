<template>
  <BasePage >
    <template v-if="!notImplemented">
    <el-card class="box-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>基本配置</span>
          <el-button type="primary" size="small" @click="savePipeline">保存配置</el-button>
        </div>
      </template>
      <el-form :model="pipeline" label-width="120px">
        <el-form-item label="名称">
          <el-input v-model="pipeline.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="pipeline.description" type="textarea" />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="pipeline.pipeline_type">
            <el-radio label="NATIVE">原生流水线</el-radio>
            <el-radio label="JENKINS">Jenkins</el-radio>
            <el-radio label="GITHUB">GitHub Actions</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- Jenkins Config -->
        <template v-if="pipeline.pipeline_type === 'JENKINS'">
          <el-divider content-position="left">Jenkins 配置</el-divider>
          <el-form-item label="Jenkins URL">
            <el-input v-model="pipeline.jenkins_url" placeholder="http://jenkins.example.com" />
          </el-form-item>
          <el-form-item label="Job Name">
            <el-input v-model="pipeline.jenkins_job_name" placeholder="my-job" />
          </el-form-item>
          <el-form-item label="API Token">
            <el-input v-model="pipeline.jenkins_token" type="password" show-password placeholder="User API Token" />
          </el-form-item>
        </template>

        <!-- GitHub Config -->
        <template v-if="pipeline.pipeline_type === 'GITHUB'">
          <el-divider content-position="left">GitHub Actions 配置</el-divider>
          <el-form-item label="Repository">
            <el-input v-model="pipeline.github_repo" placeholder="username/repo" />
          </el-form-item>
          <el-form-item label="Workflow ID">
            <el-input v-model="pipeline.github_workflow_id" placeholder="main.yml or ID" />
          </el-form-item>
          <el-form-item label="Personal Token">
            <el-input v-model="pipeline.github_token" type="password" show-password placeholder="PAT (repo scope)" />
          </el-form-item>
        </template>
        
        <el-form-item label="Webhook Token">
          <el-input v-model="pipeline.webhook_token" disabled>
             <template #append>
               <el-button @click="copyToken">复制</el-button>
             </template>
          </el-input>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 仅原生流水线显示阶段编排 -->
    <div class="stages-container" v-if="pipeline.pipeline_type === 'NATIVE'">
      <h3>阶段编排</h3>
      <el-timeline>
        <el-timeline-item v-for="(stage, index) in stages" :key="index" placement="top">
          <el-card>
            <div slot="header" class="stage-header">
              <span>阶段 {{ index + 1 }}</span>
              <el-button type="text" style="color: #f56c6c" @click="removeStage(index)">删除</el-button>
            </div>
            <el-form :model="stage" label-width="80px">
              <el-form-item label="名称">
                <el-input v-model="stage.name" />
              </el-form-item>
              <el-form-item label="类型">
                <el-select v-model="stage.execute_type">
                  <el-option label="API 测试" value="API" />
                  <el-option label="UI 测试" value="UI" />
                  <el-option label="脚本" value="SCRIPT" />
                </el-select>
              </el-form-item>
              <el-form-item label="目标 ID">
                <el-input v-model="stage.target_id" placeholder="TestPlan ID / Suite ID" />
              </el-form-item>
            </el-form>
          </el-card>
        </el-timeline-item>
        <el-timeline-item>
          <el-button type="dashed" @click="addStage" style="width: 100%">+ 添加阶段</el-button>
          <el-button type="primary" @click="saveStages" style="margin-left: 10px">保存阶段</el-button>
        </el-timeline-item>
      </el-timeline>
    </div>

    <el-divider content-position="left">构建历史</el-divider>
    
    <div style="margin-bottom: 10px;">
       <el-button type="success" @click="triggerBuild">立即构建</el-button>
    </div>

    <el-table :data="builds" style="width: 100%">
      <el-table-column prop="id" label="#" width="60" />
      <el-table-column prop="status" label="状态">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="triggered_by" label="触发者" />
      <el-table-column prop="started_at" label="开始时间" />
      <el-table-column label="外部链接" v-if="pipeline.pipeline_type !== 'NATIVE'">
        <template #default="scope">
           <a v-if="scope.row.external_url" :href="scope.row.external_url" target="_blank">View External</a>
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="scope">
          <el-popover placement="left" title="执行日志" width="600" trigger="click">
            <template #reference>
              <el-button size="small">查看日志</el-button>
            </template>
            <pre class="log-pre">{{ scope.row.logs || '暂无日志' }}</pre>
          </el-popover>
        </template>
      </el-table-column>
    </el-table>
    </template>

    <NotImplementedPlaceholder
      v-else
      module-name="CI/CD 流水线"
      :message="niMessage"
      :planned="niPlanned"
    />
  </BasePage>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '@/utils/request'
import { ElMessage } from 'element-plus'
import NotImplementedPlaceholder from '@/components/NotImplementedPlaceholder.vue'

const route = useRoute()
const router = useRouter()
const pipelineId = route.params.id

const pipeline = ref({
  name: '',
  pipeline_type: 'NATIVE',
  jenkins_url: '',
  github_repo: ''
})
const stages = ref([])
const builds = ref([])
const loading = ref(false)
const notImplemented = ref(false)
const niMessage = ref('')
const niPlanned = ref([])

const fetchData = async () => {
  loading.value = true
  try {
    // 1. Pipeline Info
    const pRes = await request.get(`/cicd/pipelines/${pipelineId}/`)
    const pData = pRes.data || {}
    if (pData.status === 'not_implemented') {
      notImplemented.value = true
      niMessage.value = pData.message || ''
      niPlanned.value = pData.planned || []
      return
    }
    pipeline.value = pData
    stages.value = pData.stages || []

    // 2. Builds
    const bRes = await request.get('/cicd/builds/', { params: { pipeline: pipelineId } })
    builds.value = bRes.data.results || bRes.data
  } catch(e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const savePipeline = async () => {
  try {
    await request.put(`/cicd/pipelines/${pipelineId}/`, pipeline.value)
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

const addStage = () => {
  stages.value.push({
    name: 'New Stage',
    execute_type: 'API',
    target_id: null,
    order: stages.value.length + 1
  })
}

const removeStage = (index) => {
  stages.value.splice(index, 1)
}

const saveStages = async () => {
  try {
    // 简化逻辑：先删除旧的再添加新的，或者后端支持批量更新
    // 这里我们假设后端足够智能，或者我们只做简单的逐个保存
    for (let i = 0; i < stages.value.length; i++) {
      const stage = stages.value[i]
      stage.pipeline = pipelineId
      stage.order = i + 1
      if (stage.id) {
        await request.put(`/cicd/stages/${stage.id}/`, stage)
      } else {
        await request.post('/cicd/stages/', stage)
      }
    }
    ElMessage.success('阶段配置已保存')
    fetchData() // 刷新以获取新的ID
  } catch (error) {
    ElMessage.error('保存阶段失败')
  }
}

const triggerBuild = async () => {
  try {
    await request.post(`/cicd/pipelines/${pipelineId}/run/`)
    ElMessage.success('构建已触发')
    setTimeout(fetchData, 1000)
  } catch (e) {
    ElMessage.error('触发失败')
  }
}

const copyToken = () => {
  navigator.clipboard.writeText(pipeline.value.webhook_token)
  ElMessage.success('Token 已复制')
}

const goBack = () => {
  router.push('/configuration/cicd/pipelines')
}

const getStatusType = (status) => {
  const map = {
    'PENDING': 'info',
    'RUNNING': 'warning',
    'SUCCESS': 'success',
    'FAILED': 'danger'
  }
  return map[status] || 'info'
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.stages-container {
  margin-top: 20px;
  padding: 20px;
  background: white;
  border-radius: 4px;
  border: 1px solid #ebeef5;
}
.stage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.log-pre {
  max-height: 300px;
  overflow-y: auto;
  background: #f5f7fa;
  padding: 10px;
  font-size: 12px;
  white-space: pre-wrap;
}
</style>
