<template>
  <div class="notification-management">
    <!-- 顶部标题 -->
    <div class="header">
      <h3>通知管理</h3>
    </div>

    <!-- Tab页 -->
    <el-tabs v-model="activeTab" class="notification-tabs">
      <!-- 通知列表Tab -->
      <el-tab-pane label="通知列表" name="list">
        <div class="tab-content">
          <!-- 筛选条件 -->
          <div class="filters">
            <el-row :gutter="20">
              <el-col :span="6">
                <el-input
                  v-model="filters.task_name"
                  placeholder="搜索任务名称"
                  clearable
                />
              </el-col>
              <el-col :span="6">
                <el-date-picker
                  v-model="filters.date_range"
                  type="daterange"
                  range-separator="至"
                  start-placeholder="开始日期"
                  end-placeholder="结束日期"
                  value-format="YYYY-MM-DD"
                />
              </el-col>
              <el-col :span="6">
                <el-button type="primary" @click="loadNotifications">
                  <el-icon><Search /></el-icon>
                  搜索
                </el-button>
                <el-button @click="resetFilters">
                  <el-icon><Refresh /></el-icon>
                  重置
                </el-button>
              </el-col>
            </el-row>
          </div>

          <!-- 通知列表 -->
          <el-table
            :data="notifications"
            v-loading="loading"
            style="width: 100%"
          >
            <el-table-column prop="task_name" label="任务名称" min-width="120" />
            <el-table-column prop="notify_time" label="通知时间" min-width="140">
              <template #default="{ row }">
                {{ formatDateTime(row.notify_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="recipients" label="收件人" min-width="120">
              <template #default="{ row }">
                <span v-if="row.notify_type === 'EMAIL'">
                  {{ row.recipients.join(', ') }}
                </span>
                <span v-else-if="row.notify_type === 'WEBHOOK'">
                  Webhook机器人
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'SUCCESS' ? 'success' : 'danger'">
                  {{ row.status === 'SUCCESS' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  size="small"
                  @click="showNotificationDetail(row)"
                >
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination">
            <el-pagination
              v-model:current-page="pagination.current"
              v-model:page-size="pagination.size"
              :total="pagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="loadNotifications"
              @current-change="loadNotifications"
            />
          </div>
        </div>
      </el-tab-pane>

      <!-- 通知配置Tab -->
      <el-tab-pane label="通知配置" name="config">
        <div class="tab-content">
          <!-- 邮箱配置 -->
          <div class="config-section">
            <h4>邮箱配置</h4>
            <el-card>
              <div class="config-form">
                <el-form :model="emailConfig" label-width="120px">
                  <el-form-item label="发件人邮箱" required>
                    <el-input
                      v-model="emailConfig.sender_email"
                      placeholder="请输入发件人邮箱"
                    />
                  </el-form-item>
                  <el-form-item label="SMTP服务器" required>
                    <el-input
                      v-model="emailConfig.smtp_host"
                      placeholder="例如：smtp.qq.com"
                    />
                  </el-form-item>
                  <el-form-item label="SMTP端口" required>
                    <el-input-number
                      v-model="emailConfig.smtp_port"
                      :min="1"
                      :max="65535"
                    />
                  </el-form-item>
                  <el-form-item label="授权码" required>
                    <el-input
                      v-model="emailConfig.smtp_password"
                      type="password"
                      placeholder="请输入邮箱授权码"
                    />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" @click="saveEmailConfig">
                      保存配置
                    </el-button>
                    <el-button @click="testEmailConfig">
                      测试连接
                    </el-button>
                  </el-form-item>
                </el-form>
              </div>
            </el-card>
          </div>

          <!-- 收件人管理 -->
          <div class="config-section">
            <h4>收件人管理</h4>
            <el-card>
              <div class="recipient-header">
                <el-button type="primary" @click="showAddRecipientDialog">
                  <el-icon><Plus /></el-icon>
                  新增收件人
                </el-button>
              </div>
              <el-table :data="recipients" style="width: 100%">
                <el-table-column prop="name" label="姓名" width="120" />
                <el-table-column prop="email" label="邮箱地址" min-width="200" />
                <el-table-column label="操作" width="120">
                  <template #default="{ row }">
                    <el-button
                      type="danger"
                      size="small"
                      @click="deleteRecipient(row)"
                    >
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </div>

          <!-- Webhook配置 -->
          <div class="config-section">
            <h4>Webhook机器人配置</h4>
            <el-card>
              <div class="webhook-header">
                <el-button type="primary" @click="showAddWebhookDialog">
                  <el-icon><Plus /></el-icon>
                  新增Webhook
                </el-button>
              </div>
              <el-table :data="webhooks" style="width: 100%">
                <el-table-column prop="name" label="名称" width="120" />
                <el-table-column prop="platform" label="平台" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getPlatformTagType(row.platform)">
                      {{ getPlatformName(row.platform) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="webhook_url" label="Webhook地址" min-width="200" />
                <el-table-column prop="enabled" label="状态" width="80">
                  <template #default="{ row }">
                    <el-switch
                      v-model="row.enabled"
                      @change="toggleWebhookStatus(row)"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120">
                  <template #default="{ row }">
                    <el-button
                      type="danger"
                      size="small"
                      @click="deleteWebhook(row)"
                    >
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 通知详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      title="通知详情"
      width="600px"
    >
      <div v-if="currentNotification" class="notification-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="任务名称">
            {{ currentNotification.task_name }}
          </el-descriptions-item>
          <el-descriptions-item label="通知时间">
            {{ formatDateTime(currentNotification.notify_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="通知类型">
            {{ currentNotification.notify_type === 'EMAIL' ? '邮箱通知' : 'Webhook通知' }}
          </el-descriptions-item>
          <el-descriptions-item label="收件人">
            <span v-if="currentNotification.notify_type === 'EMAIL'">
              {{ currentNotification.recipients.join(', ') }}
            </span>
            <span v-else>
              Webhook机器人
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentNotification.status === 'SUCCESS' ? 'success' : 'danger'">
              {{ currentNotification.status === 'SUCCESS' ? '成功' : '失败' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="内容">
            <pre class="content-pre">{{ currentNotification.content }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="错误信息" v-if="currentNotification.error_message">
            {{ currentNotification.error_message }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>

    <!-- 新增收件人对话框 -->
    <el-dialog
      v-model="showRecipientDialog"
      title="新增收件人"
      width="400px"
    >
      <el-form :model="newRecipient" label-width="80px">
        <el-form-item label="姓名" required>
          <el-input v-model="newRecipient.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱" required>
          <el-input v-model="newRecipient.email" placeholder="请输入邮箱地址" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRecipientDialog = false">取消</el-button>
        <el-button type="primary" @click="addRecipient">确定</el-button>
      </template>
    </el-dialog>

    <!-- 新增Webhook对话框 -->
    <el-dialog
      v-model="showWebhookDialog"
      title="新增Webhook机器人"
      width="500px"
    >
      <el-form :model="newWebhook" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="newWebhook.name" placeholder="请输入Webhook名称" />
        </el-form-item>
        <el-form-item label="平台" required>
          <el-select v-model="newWebhook.platform" placeholder="请选择平台">
            <el-option label="飞书" value="FEISHU" />
            <el-option label="企业微信" value="WECHAT_WORK" />
            <el-option label="钉钉" value="DINGTALK" />
          </el-select>
        </el-form-item>
        <el-form-item label="Webhook地址" required>
          <el-input
            v-model="newWebhook.webhook_url"
            placeholder="请输入Webhook地址"
            type="textarea"
            :rows="2"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showWebhookDialog = false">取消</el-button>
        <el-button type="primary" @click="addWebhook">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'

const activeTab = ref('list')
const loading = ref(false)
const showDetailDialog = ref(false)
const showRecipientDialog = ref(false)
const showWebhookDialog = ref(false)

// 筛选条件
const filters = reactive({
  task_name: '',
  date_range: []
})

// 分页配置
const pagination = reactive({
  current: 1,
  size: 10,
  total: 0
})

// 通知列表数据
const notifications = ref([])
const currentNotification = ref(null)

// 邮箱配置
const emailConfig = reactive({
  sender_email: '',
  smtp_host: '',
  smtp_port: 465,
  smtp_password: ''
})

// 收件人列表
const recipients = ref([])
const newRecipient = reactive({
  name: '',
  email: ''
})

// Webhook列表
const webhooks = ref([])
const newWebhook = reactive({
  name: '',
  platform: '',
  webhook_url: ''
})

// 加载通知列表
const loadNotifications = async () => {
  loading.value = true
  try {
    // 模拟数据
    notifications.value = [
      {
        id: 1,
        task_name: '每日API测试',
        notify_time: new Date().toISOString(),
        notify_type: 'EMAIL',
        recipients: ['user1@example.com', 'user2@example.com'],
        status: 'SUCCESS',
        content: '测试任务执行完成，共执行10个接口，成功8个，失败2个',
        error_message: ''
      },
      {
        id: 2,
        task_name: '每周数据同步',
        notify_time: new Date(Date.now() - 86400000).toISOString(),
        notify_type: 'WEBHOOK',
        recipients: [],
        status: 'FAILED',
        content: '数据同步任务执行失败',
        error_message: '网络连接超时'
      }
    ]
    pagination.total = 2
  } catch (error) {
    ElMessage.error('加载通知列表失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const resetFilters = () => {
  filters.task_name = ''
  filters.date_range = []
  loadNotifications()
}

// 显示通知详情
const showNotificationDetail = (notification) => {
  currentNotification.value = notification
  showDetailDialog.value = true
}

// 格式化日期时间
const formatDateTime = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 保存邮箱配置
const saveEmailConfig = async () => {
  try {
    ElMessage.success('邮箱配置保存成功')
  } catch (error) {
    ElMessage.error('保存邮箱配置失败')
  }
}

// 测试邮箱配置
const testEmailConfig = async () => {
  try {
    ElMessage.success('邮箱连接测试成功')
  } catch (error) {
    ElMessage.error('邮箱连接测试失败')
  }
}

// 显示新增收件人对话框
const showAddRecipientDialog = () => {
  newRecipient.name = ''
  newRecipient.email = ''
  showRecipientDialog.value = true
}

// 添加收件人
const addRecipient = async () => {
  if (!newRecipient.name || !newRecipient.email) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  recipients.value.push({ ...newRecipient })
  showRecipientDialog.value = false
  ElMessage.success('收件人添加成功')
}

// 删除收件人
const deleteRecipient = async (recipient) => {
  try {
    await ElMessageBox.confirm('确定要删除这个收件人吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const index = recipients.value.findIndex(r => r.email === recipient.email)
    if (index !== -1) {
      recipients.value.splice(index, 1)
      ElMessage.success('收件人删除成功')
    }
  } catch (error) {
    // 用户取消删除
  }
}

// 显示新增Webhook对话框
const showAddWebhookDialog = () => {
  newWebhook.name = ''
  newWebhook.platform = ''
  newWebhook.webhook_url = ''
  showWebhookDialog.value = true
}

// 添加Webhook
const addWebhook = async () => {
  if (!newWebhook.name || !newWebhook.platform || !newWebhook.webhook_url) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  webhooks.value.push({
    ...newWebhook,
    enabled: true
  })
  showWebhookDialog.value = false
  ElMessage.success('Webhook添加成功')
}

// 删除Webhook
const deleteWebhook = async (webhook) => {
  try {
    await ElMessageBox.confirm('确定要删除这个Webhook吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const index = webhooks.value.findIndex(w => w.webhook_url === webhook.webhook_url)
    if (index !== -1) {
      webhooks.value.splice(index, 1)
      ElMessage.success('Webhook删除成功')
    }
  } catch (error) {
    // 用户取消删除
  }
}

// 切换Webhook状态
const toggleWebhookStatus = async (webhook) => {
  try {
    ElMessage.success(`Webhook ${webhook.enabled ? '启用' : '禁用'}成功`)
  } catch (error) {
    webhook.enabled = !webhook.enabled
    ElMessage.error('操作失败')
  }
}

// 获取平台名称
const getPlatformName = (platform) => {
  const platformMap = {
    FEISHU: '飞书',
    WECHAT_WORK: '企业微信',
    DINGTALK: '钉钉'
  }
  return platformMap[platform] || platform
}

// 获取平台标签类型
const getPlatformTagType = (platform) => {
  const typeMap = {
    FEISHU: 'success',
    WECHAT_WORK: 'primary',
    DINGTALK: 'warning'
  }
  return typeMap[platform] || 'info'
}

// 初始化加载数据
onMounted(() => {
  loadNotifications()
  
  // 加载模拟数据
  recipients.value = [
    { name: '张三', email: 'zhangsan@example.com' },
    { name: '李四', email: 'lisi@example.com' }
  ]
  
  webhooks.value = [
    {
      name: '飞书通知',
      platform: 'FEISHU',
      webhook_url: 'https://open.feishu.cn/open-apis/bot/v2/hook/xxx',
      enabled: true
    },
    {
      name: '企业微信通知',
      platform: 'WECHAT_WORK',
      webhook_url: 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx',
      enabled: true
    }
  ]
})
</script>

<style scoped>
.notification-management {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100%;
}

.header {
  margin-bottom: 20px;
}

.header h3 {
  margin: 0;
  color: #303133;
}

.notification-tabs {
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.tab-content {
  padding: 20px;
}

.filters {
  margin-bottom: 20px;
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.config-section {
  margin-bottom: 24px;
}

.config-section h4 {
  margin: 0 0 16px 0;
  color: #303133;
  font-weight: 600;
}

.recipient-header,
.webhook-header {
  margin-bottom: 16px;
}

.notification-detail .content-pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
}
</style>