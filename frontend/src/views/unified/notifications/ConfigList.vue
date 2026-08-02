<template>
  <BasePage title="通知配置管理">
    <template #actions>
      <PremiumButton type="primary" glow @click="handleCreateConfig">
        <el-icon><Plus /></el-icon>
        新建配置
      </PremiumButton>
    </template>

    <div class="unified-config-list-wrapper">
      <PremiumCard class="filter-card" padding="16px 24px">
        <div class="filter-section">
          <el-input
            v-model="searchText"
            placeholder="搜索配置名称"
            clearable
            style="width: 250px"
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <el-select
            v-model="configTypeFilter"
            placeholder="配置类型"
            clearable
            style="width: 150px"
            @change="handleFilter"
          >
            <el-option label="飞书" value="webhook_feishu" />
            <el-option label="企业微信" value="webhook_wechat" />
            <el-option label="钉钉" value="webhook_dingtalk" />
          </el-select>

          <el-select
            v-model="statusFilter"
            placeholder="状态"
            clearable
            style="width: 150px"
            @change="handleFilter"
          >
            <el-option label="启用" value="true" />
            <el-option label="禁用" value="false" />
          </el-select>
        </div>
      </PremiumCard>

      <PremiumCard class="table-card" padding="0">
        <el-table class="premium-table" :data="configs" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="name" label="配置名称" min-width="200">
        <template #default="{ row }">
          <div class="config-name">
            <span>{{ row.name }}</span>
            <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="config_type" label="配置类型" width="120">
        <template #default="{ row }">
          <el-tag :type="getConfigTypeTag(row.config_type)" size="small">
            {{ getConfigTypeText(row.config_type) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="机器人配置" min-width="200">
        <template #default="{ row }">
          <div class="bot-list">
            <el-tag
              v-for="(bot, index) in getWebhookBots(row.webhook_bots)"
              :key="index"
              size="small"
              style="margin-right: 8px; margin-bottom: 4px"
            >
              {{ bot.name }}
            </el-tag>
            <span v-if="!getWebhookBots(row.webhook_bots).length">-</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="enable_ui_automation" label="UI自动化" width="100">
        <template #default="{ row }">
          <el-switch v-model="row.enable_ui_automation" disabled />
        </template>
      </el-table-column>

      <el-table-column prop="enable_api_testing" label="API测试" width="100">
        <template #default="{ row }">
          <el-switch v-model="row.enable_api_testing" disabled />
        </template>
      </el-table-column>

      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="testConfig(row)" :loading="row.testing">
            测试
          </el-button>
          <el-button size="small" @click="editConfig(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteConfig(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

        <div class="pagination-footer">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next, jumper"
            @current-change="handlePageChange"
          />
        </div>
      </PremiumCard>
    </div>

    <!-- 创建/编辑配置对话框 -->
    <el-dialog
      :title="isEdit ? '编辑配置' : '新建配置'"
      v-model="showDialog"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form :model="configForm" :rules="formRules" ref="formRef" label-width="120px">
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="configForm.name" placeholder="请输入配置名称" />
        </el-form-item>

        <el-form-item label="配置类型" prop="config_type">
          <el-select v-model="configForm.config_type" placeholder="请选择配置类型" style="width: 100%">
            <el-option label="飞书" value="webhook_feishu" />
            <el-option label="企业微信" value="webhook_wechat" />
            <el-option label="钉钉" value="webhook_dingtalk" />
          </el-select>
        </el-form-item>

        <el-form-item label="机器人配置">
          <div class="bot-config-list">
            <div
              v-for="(bot, index) in configForm.bots"
              :key="index"
              class="bot-config-item"
            >
              <el-row :gutter="12">
                <el-col :span="8">
                  <el-input v-model="bot.name" placeholder="机器人名称" />
                </el-col>
                <el-col :span="14">
                  <el-input v-model="bot.webhook_url" placeholder="Webhook URL" />
                </el-col>
                <el-col :span="2">
                  <el-button
                    type="danger"
                    size="small"
                    :icon="Delete"
                    @click="removeBot(index)"
                  />
                </el-col>
              </el-row>
              <el-input
                v-if="configForm.config_type === 'webhook_dingtalk'"
                v-model="bot.secret"
                placeholder="钉钉 Secret (可选)"
                style="margin-top: 8px"
              />
            </div>
            <el-button size="small" @click="addBot" :icon="Plus">
              添加机器人
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="启用范围">
          <el-checkbox v-model="configForm.enable_ui_automation">UI自动化</el-checkbox>
          <el-checkbox v-model="configForm.enable_api_testing">API测试</el-checkbox>
        </el-form-item>

        <el-form-item label="设为默认">
          <el-switch v-model="configForm.is_default" />
        </el-form-item>

        <el-form-item label="启用状态">
          <el-switch v-model="configForm.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showDialog = false">取消</el-button>
          <PremiumButton type="primary" @click="handleSave" :loading="saving" glow>保存</PremiumButton>
        </span>
      </template>
    </el-dialog>
  </BasePage>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Delete } from '@element-plus/icons-vue'
import {
  getNotificationConfigList,
  createNotificationConfig,
  updateNotificationConfig,
  deleteNotificationConfig as deleteNotificationConfigApi,
  testNotificationConfig
} from '@/api/unified/notification'

// 数据
const configs = ref([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 筛选
const searchText = ref('')
const configTypeFilter = ref('')
const statusFilter = ref('')

// 表单
const configForm = reactive({
  name: '',
  config_type: 'webhook_feishu',
  bots: [],
  enable_ui_automation: true,
  enable_api_testing: true,
  is_default: false,
  is_active: true
})

const formRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  config_type: [{ required: true, message: '请选择配置类型', trigger: 'change' }]
}

let editingId = null

// 方法
const fetchConfigs = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: searchText.value,
      config_type: configTypeFilter.value,
      is_active: statusFilter.value
    }
    const response = await getNotificationConfigList(params)
    configs.value = response.data.results || []
    total.value = response.data.count || 0
  } catch (error) {
    ElMessage.error('获取配置列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchConfigs()
}

const handleFilter = () => {
  currentPage.value = 1
  fetchConfigs()
}

const handlePageChange = () => {
  fetchConfigs()
}

const handleCreateConfig = () => {
  isEdit.value = false
  editingId = null
  Object.assign(configForm, {
    name: '',
    config_type: 'webhook_feishu',
    bots: [],
    enable_ui_automation: true,
    enable_api_testing: true,
    is_default: false,
    is_active: true
  })
  showDialog.value = true
}

const editConfig = (row) => {
  isEdit.value = true
  editingId = row.id
  const bots = getWebhookBots(row.webhook_bots).map(bot => ({
    name: bot.name,
    webhook_url: bot.webhook_url,
    secret: bot.secret || ''
  }))

  Object.assign(configForm, {
    name: row.name,
    config_type: row.config_type,
    bots,
    enable_ui_automation: row.enable_ui_automation,
    enable_api_testing: row.enable_api_testing,
    is_default: row.is_default,
    is_active: row.is_active
  })
  showDialog.value = true
}

const handleSave = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      const webhookBots = {}
      configForm.bots.forEach((bot, index) => {
        const key = `bot_${index}`
        webhookBots[key] = {
          name: bot.name,
          webhook_url: bot.webhook_url
        }
        if (bot.secret) {
          webhookBots[key].secret = bot.secret
        }
      })

      const data = {
        name: configForm.name,
        config_type: configForm.config_type,
        webhook_bots: webhookBots,
        enable_ui_automation: configForm.enable_ui_automation,
        enable_api_testing: configForm.enable_api_testing,
        is_default: configForm.is_default,
        is_active: configForm.is_active
      }

      if (isEdit.value) {
        await updateNotificationConfig(editingId, data)
        ElMessage.success('配置更新成功')
      } else {
        await createNotificationConfig(data)
        ElMessage.success('配置创建成功')
      }

      showDialog.value = false
      fetchConfigs()
    } catch (error) {
      ElMessage.error(isEdit.value ? '配置更新失败' : '配置创建失败')
      console.error(error)
    } finally {
      saving.value = false
    }
  })
}

const testConfig = async (row) => {
  row.testing = true
  try {
    await testNotificationConfig(row.id)
    ElMessage.success('测试通知发送成功')
  } catch (error) {
    ElMessage.error('测试通知发送失败')
    console.error(error)
  } finally {
    row.testing = false
  }
}

const deleteConfig = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除配置 "${row.name}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteNotificationConfigApi(row.id)
    ElMessage.success('配置删除成功')
    fetchConfigs()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('配置删除失败')
      console.error(error)
    }
  }
}

const addBot = () => {
  configForm.bots.push({
    name: '',
    webhook_url: '',
    secret: ''
  })
}

const removeBot = (index) => {
  configForm.bots.splice(index, 1)
}

// 辅助方法
const getWebhookBots = (webhookBots) => {
  if (!webhookBots) return []
  return Object.entries(webhookBots).map(([key, config]) => ({
    name: config.name || key,
    webhook_url: config.webhook_url,
    secret: config.secret
  }))
}

const getConfigTypeTag = (type) => {
  const tags = {
    webhook_feishu: 'primary',
    webhook_wechat: 'success',
    webhook_dingtalk: 'warning'
  }
  return tags[type] || 'info'
}

const getConfigTypeText = (type) => {
  const texts = {
    webhook_feishu: '飞书',
    webhook_wechat: '企业微信',
    webhook_dingtalk: '钉钉'
  }
  return texts[type] || type
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  fetchConfigs()
})
</script>

<style scoped>
.unified-config-list-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-section {
  display: flex;
  gap: 12px;
}

.config-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bot-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.bot-config-list {
  width: 100%;
}

.bot-config-item {
  margin-bottom: 12px;
}

.bot-config-item:last-child {
  margin-bottom: 0;
}
</style>
