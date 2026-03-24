<template>
  <BasePage title="节点管理">
    <template #actions><el-button type="primary" @click="loadNodes">
          <el-icon><Refresh /></el-icon>
          刷新列表
        </el-button>
        <el-button type="success" @click="showGuideDialog = true">
          <el-icon><InfoFilled /></el-icon>
          接入指南
        </el-button></template>
    
    <div class="main-content">
      <el-card class="node-list-card">
        <el-table
          v-loading="loading"
          :data="nodes"
          style="width: 100%"
          border
        >
          <el-table-column prop="name" label="节点名称" min-width="150" />
          <el-table-column prop="node_type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag :type="row.node_type === 'recorder' ? 'warning' : 'primary'">
                {{ row.node_type === 'recorder' ? '录制节点' : '执行节点' }}
              </el-tag>
            </template>
  
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="ip_address" label="IP地址" width="150" />
          <el-table-column prop="last_heartbeat" label="最后心跳" width="180">
            <template #default="{ row }">
              {{ formatTime(row.last_heartbeat) }}
            </template>
          </el-table-column>
          <el-table-column prop="capabilities" label="能力" min-width="200" show-overflow-tooltip>
             <template #default="{ row }">
              {{ formatCapabilities(row.capabilities) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button
                type="danger"
                size="small"
                link
                @click="handleDelete(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="total"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-card>
    </div>

    <!-- 接入指南对话框 -->
    <el-dialog
      v-model="showGuideDialog"
      title="节点接入指南"
      width="650px"
    >
      <div class="guide-content">
        <el-tabs v-model="activeGuideTab">
          <el-tab-pane label="录制节点" name="recorder">
             <el-alert
              title="录制节点说明"
              type="info"
              description="录制节点用于在本地启动浏览器进行用例录制，并自动同步到云端。"
              show-icon
              :closable="false"
              style="margin-bottom: 20px"
            />
            <p>1. 确保本地安装 Python 3 和 Playwright:</p>
            <div class="code-block">
              <code>pip install playwright requests</code>
              <br>
              <code>playwright install</code>
            </div>
            <p>2. 运行录制代理命令:</p>
            <div class="code-block">
              <code>{{ recorderCommand }}</code>
              <el-button link type="primary" @click="copyCommand(recorderCommand)">
                <el-icon><CopyDocument /></el-icon> 复制
              </el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="执行节点" name="executor">
            <el-alert
              title="执行节点说明 (开发中)"
              type="warning"
              description="执行节点用于分担服务器压力，在远程机器上运行测试任务。目前该功能尚在开发完善中。"
              show-icon
              :closable="false"
              style="margin-bottom: 20px"
            />
            <p>即将推出...</p>
          </el-tab-pane>
        </el-tabs>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showGuideDialog = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  
  </BasePage>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, InfoFilled, CopyDocument } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { getExecutionNodes, deleteExecutionNode } from '@/api/ui_automation'

const userStore = useUserStore()
const loading = ref(false)
const nodes = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const showGuideDialog = ref(false)
const activeGuideTab = ref('recorder')

const recorderCommand = computed(() => {
  const origin = window.location.origin
  const token = userStore.accessToken || '<YOUR_TOKEN>'
  // 这里 Project ID 暂时用占位符，因为这是全局配置
  return `python tools/recorder_agent.py --server ${origin} --project <PROJECT_ID> --token ${token}`
})

const loadNodes = async () => {
  loading.value = true
  try {
    const res = await getExecutionNodes({
      page: currentPage.value,
      page_size: pageSize.value
    })
    
    if (res.data && Array.isArray(res.data.results)) {
      nodes.value = res.data.results
      total.value = res.data.count
    } else if (Array.isArray(res.data)) {
      nodes.value = res.data
      total.value = res.data.length
    } else if (res.results && Array.isArray(res.results)) {
      nodes.value = res.results
      total.value = res.count
    } else {
      nodes.value = []
      total.value = 0
    }
  } catch (error) {
    console.error('获取节点列表失败:', error)
    const msg = error.response?.data?.detail || error.message || '获取节点列表失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除节点 "${row.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await deleteExecutionNode(row.id)
    ElMessage.success('删除成功')
    loadNodes()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除节点失败:', error)
      const msg = error.response?.data?.detail || error.message || '删除失败'
      ElMessage.error(msg)
    }
  }
}

const copyCommand = (text) => {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('命令已复制')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

const handleSizeChange = (val) => {
  pageSize.value = val
  loadNodes()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadNodes()
}

const getStatusType = (status) => {
  const map = {
    'online': 'success',
    'offline': 'info',
    'busy': 'warning'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    'online': '在线',
    'offline': '离线',
    'busy': '忙碌'
  }
  return map[status] || status
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

const formatCapabilities = (caps) => {
  if (!caps) return '-'
  try {
    const obj = typeof caps === 'string' ? JSON.parse(caps) : caps
    return JSON.stringify(obj)
  } catch (e) {
    return String(caps)
  }
}

onMounted(() => {
  loadNodes()
})
</script>

<style scoped>
.agent-management {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}





.main-content {
  flex: 1;
  overflow: hidden;
}

.node-list-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.node-list-card :deep(.el-card__body) {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.guide-content {
  padding: 10px;
}

.code-block {
  background: #2d2d2d;
  padding: 15px;
  border-radius: 4px;
  margin: 10px 0;
  position: relative;
}

.code-block code {
  color: #67c23a;
  font-family: monospace;
  word-break: break-all;
  display: block;
  margin-bottom: 5px;
}

.code-block .el-button {
  position: absolute;
  top: 10px;
  right: 10px;
}
</style>
