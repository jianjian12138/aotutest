<template>
  <div class="debug-file-manager">
    <div class="page-header">
      <h2>调试文件管理</h2>
      <el-button type="primary" @click="refreshList">刷新列表</el-button>
    </div>
    
    <el-card class="box-card">
      <el-table :data="fileList" style="width: 100%" v-loading="loading">
        <el-table-column prop="project_name" label="项目" width="180" />
        <el-table-column prop="case_name" label="用例" width="220" />
        <el-table-column prop="step_info" label="步骤" width="150" />
        <el-table-column prop="filename" label="文件名" min-width="250" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.type === 'json' ? 'info' : 'success'">
              {{ scope.row.type.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100">
          <template #default="scope">
            {{ formatSize(scope.row.size) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="viewFile(scope.row)">查看</el-button>
            <el-button link type="primary" :href="scope.row.url" target="_blank">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 预览对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="currentFile?.filename"
      width="70%"
      destroy-on-close
    >
      <div v-loading="contentLoading" class="preview-container">
        <div v-if="currentFile?.type === 'image'" class="image-preview">
          <img :src="currentFile.url" style="max-width: 100%" />
        </div>
        <div v-else-if="currentFile?.type === 'json'" class="json-preview">
          <pre>{{ jsonContent }}</pre>
        </div>
        <el-empty v-else description="不支持预览" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDebugFiles, getDebugFileContent } from '@/api/ui_automation'
import dayjs from 'dayjs'

const fileList = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const currentFile = ref(null)
const jsonContent = ref('')
const contentLoading = ref(false)

const refreshList = async () => {
  loading.value = true
  try {
    const res = await getDebugFiles()
    fileList.value = res.data || []
    ElMessage.success('刷新成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('获取列表失败')
  } finally {
    loading.value = false
  }
}

const viewFile = async (file) => {
  currentFile.value = file
  dialogVisible.value = true
  
  if (file.type === 'json') {
    contentLoading.value = true
    try {
      const res = await getDebugFileContent(file.url)
      jsonContent.value = JSON.stringify(res.data, null, 2)
    } catch (error) {
      console.error(error)
      ElMessage.error('获取文件内容失败')
      jsonContent.value = '加载失败'
    } finally {
      contentLoading.value = false
    }
  }
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  refreshList()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.preview-container {
  min-height: 200px;
  max-height: 600px;
  overflow: auto;
}
.json-preview pre {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}
.image-preview {
  text-align: center;
}
</style>
