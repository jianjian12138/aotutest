<template>
  <div class="device-management">
    <div class="page-header">
      <h1 class="page-title">设备管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          刷新设备列表
        </el-button>
        <el-button type="success" @click="showConnectDialog = true">
          <el-icon><Connection /></el-icon>
          连接远程设备
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <el-card class="device-list-card">
        <el-table
          v-loading="loading"
          :data="devices"
          style="width: 100%"
          border
        >
          <el-table-column prop="name" label="设备名称" min-width="150" />
          <el-table-column prop="device_id" label="设备ID" min-width="180" show-overflow-tooltip />
          <el-table-column prop="platform" label="平台" width="100">
            <template #default="{ row }">
              <el-tag :type="getPlatformType(row.platform)">
                <el-icon class="platform-icon">
                  <component :is="row.platform === 'android' ? 'PlatformAndroid' : 'Iphone'" />
                </el-icon>
                {{ row.platform === 'android' ? 'Android' : 'iOS' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag effect="plain">{{ row.type === 'real' ? '真机' : '模拟器' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="version" label="系统版本" width="120" />
          <el-table-column prop="last_online" label="最后在线时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.last_online) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'online'"
                type="danger"
                size="small"
                link
                @click="handleDisconnect(row)"
              >
                断开连接
              </el-button>
              <el-button
                v-else-if="row.platform === 'android' && row.device_id.includes(':')"
                type="primary"
                size="small"
                link
                @click="handleReconnect(row)"
              >
                重连
              </el-button>
              <span v-else class="text-gray">-</span>
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

    <!-- 连接远程设备对话框 -->
    <el-dialog
      v-model="showConnectDialog"
      title="连接远程 Android 设备"
      width="400px"
    >
      <el-form :model="connectForm" label-width="80px">
        <el-form-item label="IP地址" required>
          <el-input v-model="connectForm.ip" placeholder="例如: 192.168.1.100" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input v-model="connectForm.port" placeholder="默认: 5555" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showConnectDialog = false">取消</el-button>
          <el-button type="primary" @click="handleConnect" :loading="connecting">
            连接
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Connection, Iphone } from '@element-plus/icons-vue'
// Note: Element Plus doesn't have a built-in Android icon, we might need a custom one or just use text/tag
// Using a placeholder component for Android icon if needed, or just relying on text

import {
  getDeviceList,
  refreshDeviceList,
  connectRemoteDevice,
  disconnectDevice
} from '@/api/ui_automation'

// 数据
const loading = ref(false)
const devices = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const showConnectDialog = ref(false)
const connecting = ref(false)
const connectForm = reactive({
  ip: '',
  port: '5555'
})

// 方法
const loadDevices = async () => {
  loading.value = true
  try {
    const res = await getDeviceList({
      page: currentPage.value,
      page_size: pageSize.value
    })
    devices.value = res.data.results
    total.value = res.data.count
  } catch (error) {
    console.error('获取设备列表失败:', error)
    ElMessage.error('获取设备列表失败')
  } finally {
    loading.value = false
  }
}

const handleRefresh = async () => {
  loading.value = true
  try {
    const res = await refreshDeviceList()
    ElMessage.success(`刷新成功，发现 ${res.data.count} 个设备`)
    await loadDevices()
  } catch (error) {
    console.error('刷新设备列表失败:', error)
    ElMessage.error('刷新设备列表失败')
  } finally {
    loading.value = false
  }
}

const handleConnect = async () => {
  if (!connectForm.ip) {
    ElMessage.warning('请输入IP地址')
    return
  }

  connecting.value = true
  try {
    await connectRemoteDevice(connectForm.ip, connectForm.port)
    ElMessage.success('连接成功')
    showConnectDialog.value = false
    connectForm.ip = ''
    connectForm.port = '5555'
    await loadDevices()
  } catch (error) {
    console.error('连接设备失败:', error)
    const msg = error.response?.data?.error || error.message || '连接失败'
    ElMessage.error(msg)
  } finally {
    connecting.value = false
  }
}

const handleReconnect = async (row) => {
  const [ip, port] = row.device_id.split(':')
  if (!ip) return

  loading.value = true
  try {
    await connectRemoteDevice(ip, port || '5555')
    ElMessage.success('重连成功')
    await loadDevices()
  } catch (error) {
    console.error('重连失败:', error)
    ElMessage.error('重连失败')
  } finally {
    loading.value = false
  }
}

const handleDisconnect = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要断开设备 ${row.name} 吗？`,
      '确认断开',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await disconnectDevice(row)
    ElMessage.success('断开成功')
    await loadDevices()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('断开失败:', error)
      ElMessage.error('断开失败')
    }
  }
}

const handleSizeChange = (val) => {
  pageSize.value = val
  loadDevices()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadDevices()
}

// 辅助函数
const getPlatformType = (platform) => {
  return platform === 'android' ? 'success' : 'info' // iOS用灰色，Android用绿色
}

const getStatusType = (status) => {
  const map = {
    'online': 'success',
    'offline': 'info',
    'busy': 'warning',
    'unauthorized': 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    'online': '在线',
    'offline': '离线',
    'busy': '忙碌',
    'unauthorized': '未授权'
  }
  return map[status] || status
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

onMounted(() => {
  loadDevices()
})
</script>

<style scoped>
.device-management {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.main-content {
  flex: 1;
  overflow: hidden;
}

.device-list-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.device-list-card :deep(.el-card__body) {
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

.platform-icon {
  margin-right: 4px;
  vertical-align: middle;
}

.text-gray {
  color: #909399;
}
</style>
