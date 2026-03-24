<template>
  <BasePage title="流水线管理">
    <template #actions>
      <el-button type="primary" @click="showCreateDialog">新建流水线</el-button>
    </template>
    
    <el-table :data="pipelines" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'info'">
            {{ scope.row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="180" />
      <el-table-column label="操作" width="250">
        <template #default="scope">
          <el-button size="small" @click="viewDetail(scope.row.id)">详情</el-button>
          <el-button size="small" type="success" @click="triggerPipeline(scope.row.id)">触发</el-button>
          <el-button size="small" type="danger" @click="deletePipeline(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create Dialog -->
    <el-dialog v-model="dialogVisible" title="新建流水线" width="50%">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input type="textarea" v-model="form.description" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="createPipeline">创建</el-button>
        </span>
      </template>
    </el-dialog>
  </BasePage>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const pipelines = ref([])
const loading = ref(false)
const dialogVisible = ref(false)

const form = reactive({
  name: '',
  description: ''
})

const fetchPipelines = async () => {
  loading.value = true
  try {
    const res = await request.get('/cicd/pipelines/')
    pipelines.value = res.data.results || res.data
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  dialogVisible.value = true
}

const createPipeline = async () => {
  try {
    // Generate a random token for webhook
    const token = Math.random().toString(36).substring(2) + Date.now().toString(36)
    
    await request.post('/cicd/pipelines/', {
      ...form,
      webhook_token: token
    })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchPipelines()
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

const viewDetail = (id) => {
  router.push(`/configuration/cicd/pipelines/${id}`)
}

const triggerPipeline = async (id) => {
  try {
    await request.post(`/cicd/pipelines/${id}/trigger/`)
    ElMessage.success('流水线已触发')
  } catch (error) {
    ElMessage.error('触发失败')
  }
}

const deletePipeline = (id) => {
  ElMessageBox.confirm('确定删除该流水线吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    await request.delete(`/cicd/pipelines/${id}/`)
    ElMessage.success('删除成功')
    fetchPipelines()
  })
}

onMounted(() => {
  fetchPipelines()
})
</script>

<style scoped>
/* 页面特定样式 */





</style>