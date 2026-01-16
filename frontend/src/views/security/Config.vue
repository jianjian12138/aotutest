<template>
  <div class="config">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>配置管理</h2>
        </div>
      </template>
      
      <!-- 配置选项卡 -->
      <el-tabs v-model="activeTab" type="border-card" style="margin-bottom: 20px;">
        <el-tab-pane label="扫描配置" name="scan">
          <el-form label-position="top" :model="scanConfig" label-width="120px">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="扫描超时时间 (秒)">
                  <el-input-number v-model="scanConfig.timeout" :min="30" :max="3600" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="最大并发数">
                  <el-input-number v-model="scanConfig.concurrent_scans" :min="1" :max="10" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="扫描深度">
                  <el-slider v-model="scanConfig.scan_depth" :min="1" :max="10" :marks="{ 1: '浅', 5: '中', 10: '深' }" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="漏洞级别阈值">
                  <el-select v-model="scanConfig.severity_threshold" placeholder="请选择漏洞级别阈值">
                    <el-option label="仅高危" value="high" />
                    <el-option label="高危+中危" value="medium" />
                    <el-option label="全部" value="low" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="排除路径">
              <el-input
                v-model="scanConfig.exclude_paths"
                type="textarea"
                placeholder="每行一个路径，例如: /admin, /static"
                :rows="4"
              />
            </el-form-item>
            <el-form-item label="排除文件类型">
              <el-input
                v-model="scanConfig.exclude_file_types"
                placeholder="用逗号分隔，例如: .jpg,.png,.css"
              />
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="告警配置" name="alarm">
          <el-form label-position="top" :model="alarmConfig" label-width="120px">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="邮件告警">
                  <el-switch v-model="alarmConfig.email_alarm" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="短信告警">
                  <el-switch v-model="alarmConfig.sms_alarm" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="告警收件人">
                  <el-input
                    v-model="alarmConfig.email_recipients"
                    type="textarea"
                    placeholder="每行一个邮箱地址"
                    :rows="3"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="告警手机号">
                  <el-input
                    v-model="alarmConfig.sms_recipients"
                    type="textarea"
                    placeholder="每行一个手机号"
                    :rows="3"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="告警模板">
              <el-select v-model="alarmConfig.alarm_template" placeholder="请选择告警模板">
                <el-option label="默认模板" value="default" />
                <el-option label="详细模板" value="detailed" />
                <el-option label="简洁模板" value="simple" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="集成配置" name="integration">
          <el-form label-position="top" :model="integrationConfig" label-width="120px">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="Jira集成">
                  <el-switch v-model="integrationConfig.jira_integration" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Slack集成">
                  <el-switch v-model="integrationConfig.slack_integration" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="Jira服务器地址" v-if="integrationConfig.jira_integration">
              <el-input v-model="integrationConfig.jira_server_url" placeholder="例如: https://your-jira.atlassian.net" />
            </el-form-item>
            <el-form-item label="Jira用户名" v-if="integrationConfig.jira_integration">
              <el-input v-model="integrationConfig.jira_username" />
            </el-form-item>
            <el-form-item label="Jira API Token" v-if="integrationConfig.jira_integration">
              <el-input v-model="integrationConfig.jira_api_token" type="password" show-password />
            </el-form-item>
            <el-form-item label="Slack Webhook URL" v-if="integrationConfig.slack_integration">
              <el-input v-model="integrationConfig.slack_webhook_url" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      
      <!-- 保存按钮 -->
      <div class="save-button-container">
        <el-button type="primary" @click="handleSaveConfig">
          <el-icon><Check /></el-icon>
          保存配置
        </el-button>
        <el-button @click="handleResetConfig">
          <el-icon><RefreshRight /></el-icon>
          重置
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, RefreshRight } from '@element-plus/icons-vue'

// 激活的标签页
const activeTab = ref('scan')

// 扫描配置
const scanConfig = reactive({
  timeout: 300,
  concurrent_scans: 5,
  scan_depth: 5,
  severity_threshold: 'medium',
  exclude_paths: '/admin\n/static',
  exclude_file_types: '.jpg,.png,.css,.js'
})

// 告警配置
const alarmConfig = reactive({
  email_alarm: true,
  sms_alarm: false,
  email_recipients: 'admin@example.com\nsecurity@example.com',
  sms_recipients: '',
  alarm_template: 'default'
})

// 集成配置
const integrationConfig = reactive({
  jira_integration: false,
  slack_integration: true,
  jira_server_url: '',
  jira_username: '',
  jira_api_token: '',
  slack_webhook_url: ''
})

// 保存配置
const handleSaveConfig = () => {
  ElMessage.success('配置保存成功')
}

// 重置配置
const handleResetConfig = () => {
  // 重置逻辑
  ElMessage.info('配置已重置')
}
</script>

<style scoped>
.config {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.save-button-container {
  margin-top: 20px;
  text-align: right;
}
</style>