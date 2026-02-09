<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">智能元素侦测 (Smart Inspector)</h1>
    </div>

    <div class="card-container">
        <el-row :gutter="20">
            <el-col :span="24">
            <div class="section-title">目标源</div>
            <div style="margin-bottom: 20px;">
                <el-radio-group v-model="inspectMode">
                    <el-radio-button label="url">URL 链接</el-radio-button>
                    <el-radio-button label="image">上传图片</el-radio-button>
                    <el-radio-button label="device">ADB 设备</el-radio-button>
                </el-radio-group>
            </div>

            <div v-if="inspectMode === 'url'">
                <div style="margin-bottom: 10px; color: #666; font-size: 14px;">
                    输入目标 URL，AI 将自动启动浏览器分析页面结构，并生成适用于 Playwright, Selenium, Appium 和 Airtest 的元素定位符。
                </div>
                <el-input v-model="inspectorUrl" placeholder="请输入目标 URL (例如 https://www.saucedemo.com)" class="input-with-select" @keyup.enter="handleInspect">
                    <template #append>
                        <el-button @click="handleInspect" :loading="inspecting" :icon="Search">开始侦测</el-button>
                    </template>
                </el-input>
            </div>

            <div v-else-if="inspectMode === 'image'">
                <div style="margin-bottom: 10px; color: #666; font-size: 14px;">
                    上传页面截图，AI 将基于视觉识别交互元素。注意：图片模式下仅支持 Airtest 图像识别和坐标定位，无法生成 CSS/XPath 选择器。
                </div>
                <el-upload
                    class="upload-demo"
                    drag
                    action="#"
                    :auto-upload="false"
                    :limit="1"
                    :on-change="handleFileChange"
                    :on-remove="handleFileRemove"
                    list-type="picture"
                >
                    <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                    <div class="el-upload__text">
                        将截图拖到此处或 <em>点击上传</em>
                    </div>
                </el-upload>
                <div style="margin-top: 15px;">
                    <el-button type="primary" @click="handleInspect" :loading="inspecting" :disabled="!inspectorImage">开始侦测</el-button>
                </div>
            </div>

            <div v-else-if="inspectMode === 'device'">
                <div style="margin-bottom: 10px; color: #666; font-size: 14px;">
                    连接 ADB 设备，直接截取当前屏幕进行 AI 识别。支持生成 Airtest 图像代码和 Appium 文本定位符。
                </div>
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 15px;">
                    <el-select v-model="selectedDeviceId" placeholder="选择设备" style="width: 300px">
                        <el-option 
                            v-for="device in devices" 
                            :key="device.id" 
                            :label="`${device.name} (${device.device_id})`" 
                            :value="device.device_id" 
                        />
                    </el-select>
                    <el-button :icon="Refresh" circle @click="handleRefreshDevices" :loading="refreshingDevices" title="刷新设备列表"></el-button>
                    <el-button type="primary" @click="handleInspect" :loading="inspecting" :disabled="!selectedDeviceId">
                        <el-icon><Cellphone /></el-icon> 截屏并侦测
                    </el-button>
                </div>
            </div>
            </el-col>
        </el-row>
        
        <el-row :gutter="20" style="margin-top: 20px" v-if="inspectionResult">
            <el-col :span="10">
                <div class="section-title">页面快照</div>
                <el-image 
                    :src="inspectionResult.screenshot_url" 
                    :preview-src-list="[inspectionResult.screenshot_url]"
                    fit="contain" 
                    style="width: 100%; border: 1px solid #dcdfe6; border-radius: 4px;"
                />
            </el-col>
            <el-col :span="14">
                <div class="section-title">识别到的元素 ({{ inspectionResult.elements.length }})</div>
                <el-table :data="inspectionResult.elements" height="600" border stripe>
                <el-table-column label="预览" width="120">
                    <template #default="scope">
                        <el-image 
                            v-if="scope.row.crop_url"
                            :src="scope.row.crop_url" 
                            :preview-src-list="[scope.row.crop_url]"
                            fit="contain" 
                            style="width: 100px; height: 50px; background: #f5f7fa"
                        />
                        <span v-else>无预览</span>
                    </template>
                </el-table-column>
                <el-table-column label="元素信息" width="180">
                    <template #default="scope">
                        <div style="font-size: 12px">
                            <div><el-tag size="small">{{ scope.row.tagName || 'UI Element' }}</el-tag></div>
                            <div v-if="scope.row.text" style="margin-top: 5px; color: #409eff; font-weight: bold">{{ scope.row.text }}</div>
                            <div style="margin-top: 5px; color: #909399">ID: {{ scope.row.id }}</div>
                        </div>
                    </template>
                </el-table-column>
                <el-table-column label="定位符 (Locators)">
                    <template #default="scope">
                        <el-tabs type="border-card" style="height: 150px">
                            <el-tab-pane label="Playwright" name="pw" v-if="scope.row.locators.playwright">
                                <el-input type="textarea" v-model="scope.row.locators.playwright" readonly resize="none" :rows="3" />
                            </el-tab-pane>
                            <el-tab-pane label="Selenium" name="se" v-if="scope.row.locators.selenium">
                                <el-input type="textarea" v-model="scope.row.locators.selenium" readonly resize="none" :rows="3" />
                            </el-tab-pane>
                            <el-tab-pane label="Appium" name="ap">
                                <el-input type="textarea" v-model="scope.row.locators.appium" readonly resize="none" :rows="3" />
                            </el-tab-pane>
                            <el-tab-pane label="Airtest" name="at">
                                <el-input type="textarea" v-model="scope.row.locators.airtest" readonly resize="none" :rows="3" />
                            </el-tab-pane>
                        </el-tabs>
                    </template>
                </el-table-column>
                </el-table>
            </el-col>
        </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, UploadFilled, Refresh, Cellphone } from '@element-plus/icons-vue'
import request from '@/utils/api'
import { getDeviceList, refreshDeviceList } from '@/api/ui_automation'

const inspectMode = ref('url')
const inspectorUrl = ref('https://www.saucedemo.com')
const inspectorImage = ref(null)
const inspecting = ref(false)
const inspectionResult = ref(null)

// Device related
const devices = ref([])
const selectedDeviceId = ref('')
const refreshingDevices = ref(false)
const deviceScreenshot = ref(null)

const loadDevices = async () => {
    try {
        const res = await getDeviceList()
        // 兼容处理：检查 res.data.results (分页) 或 res.data (不分页)
        const data = res.data || res
        devices.value = data.results || data || []
        
        if (devices.value.length > 0 && !selectedDeviceId.value) {
            selectedDeviceId.value = devices.value[0].device_id
        }
    } catch (error) {
        console.error('Failed to load devices:', error)
    }
}

const handleRefreshDevices = async () => {
    refreshingDevices.value = true
    try {
        await refreshDeviceList()
        await loadDevices()
        ElMessage.success('设备列表已更新')
    } catch (error) {
        ElMessage.error('刷新失败')
    } finally {
        refreshingDevices.value = false
    }
}

const handleFileChange = (file) => {
    inspectorImage.value = file.raw
}

const handleFileRemove = () => {
    inspectorImage.value = null
}

const handleInspect = async () => {
    if (inspectMode.value === 'url' && !inspectorUrl.value) {
        ElMessage.warning('请输入 URL')
        return
    }
    if (inspectMode.value === 'image' && !inspectorImage.value) {
        ElMessage.warning('请上传图片')
        return
    }
    if (inspectMode.value === 'device' && !selectedDeviceId.value) {
        ElMessage.warning('请选择设备')
        return
    }

    inspecting.value = true
    inspectionResult.value = null
    
    try {
        let response;
        if (inspectMode.value === 'url') {
            response = await request.post('/ui-automation/ai-execution-records/inspect_page/', {
                url: inspectorUrl.value
            })
        } else if (inspectMode.value === 'image') {
            const formData = new FormData()
            formData.append('image', inspectorImage.value)
            // Axios automatically sets Content-Type to multipart/form-data when data is FormData
            // However, our request wrapper might be interfering. Let's ensure headers are set if needed,
            // or just rely on standard behavior.
            // Note: request helper usually handles JSON. For FormData, we might need to be careful.
            
            // Let's try passing headers explicitly if the wrapper supports it, or use raw axios if needed.
            // Assuming the existing request wrapper handles FormData correctly (it usually does if it doesn't force JSON)
            response = await request.post('/ui-automation/ai-execution-records/inspect_page/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            })
        } else if (inspectMode.value === 'device') {
            response = await request.post('/ui-automation/ai-execution-records/inspect_page/', {
                device_id: selectedDeviceId.value
            })
        }
        
        inspectionResult.value = response.data
        ElMessage.success('侦测完成')
    } catch (error) {
        console.error('Inspection failed:', error)
        ElMessage.error('侦测失败: ' + (error.response?.data?.error || error.message))
    } finally {
        inspecting.value = false
    }
}

onMounted(() => {
    loadDevices()
})
</script>

<style lang="scss" scoped>
.page-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
  
  .page-title {
    font-size: 20px;
    font-weight: 600;
    margin: 0;
  }
}

.card-container {
  background-color: #fff;
  border-radius: 4px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  min-height: calc(100vh - 100px);
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 15px;
  padding-left: 10px;
  border-left: 4px solid #409eff;
}
</style>