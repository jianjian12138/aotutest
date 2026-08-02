<template>
  <div class="vanna-config-selector">
    <el-select
      v-model="selectedConfigId"
      :placeholder="placeholder"
      clearable
      :style="{ width: width }"
      :disabled="loading"
    >
      <template #prepend>
        <el-icon v-if="loading"><Loading /></el-icon>
        <el-icon v-else><Setting /></el-icon>
      </template>
      <el-option
        v-for="config in configs"
        :key="config.id"
        :label="config.name"
        :value="config.id"
      >
        <div class="config-option">
          <div class="config-name">{{ config.name }}</div>
          <div class="config-desc">{{ config.description }}</div>
          <div class="config-model">{{ config.model_name }}</div>
          <div class="config-status">
            <el-tag
              :type="config.status === 'ACTIVE' ? 'success' : 'warning'"
              size="small"
            >
              {{ config.status === 'ACTIVE' ? '启用' : '禁用' }}
            </el-tag>
          </div>
        </div>
      </el-option>
      <el-option
        v-if="configs.length === 0 && !loading"
        :key="0"
        :label="'暂无配置'"
        :disabled="true"
      />
    </el-select>
    <slot name="actions"></slot>
  </div>
</template>

<script setup>
import { ref, onMounted, defineProps, defineEmits, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Loading } from '@element-plus/icons-vue'
import { getVannaConfigs } from '@/api/data-factory'

// Props
const props = defineProps({
  modelValue: {
    type: [Number, String, null],
    default: null
  },
  placeholder: {
    type: String,
    default: '选择Vanna AI配置'
  },
  width: {
    type: String,
    default: '300px'
  },
  autoLoad: {
    type: Boolean,
    default: true
  },
  showActions: {
    type: Boolean,
    default: true
  }
})

// Emits
const emit = defineEmits(['update:modelValue', 'configChanged', 'loadConfigs'])

// 状态管理
const loading = ref(false)
const configs = ref([])
const selectedConfigId = ref(props.modelValue)

// 监听外部值变化
watch(
  () => props.modelValue,
  (newValue) => {
    selectedConfigId.value = newValue
  }
)

// 监听内部值变化
watch(
  selectedConfigId,
  (newValue) => {
    emit('update:modelValue', newValue)
    emit('configChanged', newValue)
  }
)

// 加载配置
const loadConfigs = async () => {
  try {
    loading.value = true
    // 实际项目中调用API
    // const response = await getVannaConfigs()
    // configs.value = response.data
    
    // 模拟Vanna配置数据
    configs.value = [
      { id: 1, name: '默认配置', description: '默认的Vanna AI配置，用于测试和开发', model_name: 'vanna-3.0', status: 'ACTIVE' },
      { id: 2, name: '生产环境配置', description: '生产环境使用的Vanna AI配置', model_name: 'vanna-3.0', status: 'ACTIVE' },
      { id: 3, name: '开发环境配置', description: '开发环境使用的Vanna AI配置', model_name: 'vanna-2.0', status: 'INACTIVE' }
    ]
    
    emit('loadConfigs', configs.value)
  } catch (error) {
    console.error('加载Vanna配置失败:', error)
    ElMessage.error('加载Vanna配置失败')
  } finally {
    loading.value = false
  }
}

// 生命周期钩子
onMounted(() => {
  if (props.autoLoad) {
    loadConfigs()
  }
})

// 暴露方法
defineExpose({
  loadConfigs
})
</script>

<style scoped>
.vanna-config-selector {
  display: inline-flex;
  align-items: center;
}

.config-option {
  padding: 8px 0;
  min-width: 200px;
}

.config-name {
  font-weight: bold;
  color: #333;
  margin-bottom: 4px;
}

.config-desc {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.config-model {
  font-size: 0.8rem;
  color: #999;
  margin-bottom: 4px;
}

.config-status {
  display: flex;
  justify-content: flex-start;
}
</style>