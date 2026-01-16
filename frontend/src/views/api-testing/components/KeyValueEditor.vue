<template>
  <div class="key-value-editor">
    <div class="header">
      <div class="column key-column">Key</div>
      <div class="column value-column">Value</div>
      <div class="column description-column">Description</div>
      <div class="column action-column"></div>
    </div>
    
    <div class="rows">
      <div
        v-for="(row, index) in rows"
        :key="index"
        class="row"
        :class="{ disabled: !row.enabled }"
      >
        <div class="column key-column">
          <el-checkbox v-model="row.enabled" @change="updateValue" />
          <el-input
            v-model="row.key"
            :placeholder="placeholderKey"
            size="small"
            @input="updateValue"
          />
        </div>
        
        <div class="column value-column">
          <el-input
            v-if="!showFile || row.type !== 'file'"
            v-model="row.value"
            :placeholder="placeholderValue"
            size="small"
            @input="updateValue"
          />
          <el-upload
            v-else
            :auto-upload="false"
            :show-file-list="false"
            @change="(file) => handleFileChange(index, file)"
          >
            <el-button size="small">选择文件</el-button>
          </el-upload>
          <span v-if="row.file" class="file-name">{{ row.file.name }}</span>
        </div>
        
        <div class="column description-column">
          <el-input
            v-model="row.description"
            placeholder="描述"
            size="small"
            @input="updateValue"
          />
        </div>
        
        <div class="column action-column">
          <el-select
            v-if="showFile"
            v-model="row.type"
            size="small"
            style="width: 70px; margin-right: 5px;"
            @change="updateValue"
          >
            <el-option label="Text" value="text" />
            <el-option label="File" value="file" />
          </el-select>
          
          <el-button
            size="small"
            type="danger"
            :icon="Delete"
            @click="removeRow(index)"
            :disabled="rows.length <= 1"
          />
        </div>
      </div>
    </div>
    
    <div class="footer">
      <el-button size="small" @click="addRow">
        <el-icon><Plus /></el-icon>
        添加行
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Plus, Delete } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  },
  placeholderKey: {
    type: String,
    default: 'Key'
  },
  placeholderValue: {
    type: String,
    default: 'Value'
  },
  showFile: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const rows = ref([])

const initializeRows = () => {
  const data = props.modelValue || {}
  console.log('KeyValueEditor initializeRows called with data:', data)
  const newRows = []
  
  // 检查数据是否为数组格式（来自convertObjectToKeyValueArray）
  if (Array.isArray(data)) {
    console.log('Data is array, processing...')
    // 如果是数组，直接使用
    newRows.push(...data.map(item => ({
      enabled: item.enabled !== false,
      key: item.key || '',
      value: item.value || '',
      description: item.description || '',
      type: item.type || 'text',
      file: item.file || null
    })))
  } else {
    console.log('Data is object, converting...')
    // 如果是对象，转换为行数据
    Object.keys(data).forEach(key => {
      if (key && data[key] !== undefined) {
        newRows.push({
          enabled: true,
          key,
          value: data[key],
          description: '',
          type: 'text',
          file: null
        })
      }
    })
  }
  
  // 确保至少有一个空行
  if (newRows.length === 0) {
    newRows.push({
      enabled: true,
      key: '',
      value: '',
      description: '',
      type: 'text',
      file: null
    })
  }
  
  console.log('KeyValueEditor final rows:', newRows)
  rows.value = newRows
}

const updateValue = () => {
  // 发送完整的行数据数组，而不是简化的key-value对象
  const result = rows.value.filter(row => row.key || row.value || row.description).map(row => ({
    key: row.key || '',
    value: row.value || '',
    description: row.description || '',
    enabled: row.enabled !== false,
    type: row.type || 'text'
  }))
  
  console.log('KeyValueEditor updateValue result (full format):', result)
  emit('update:modelValue', result)
  
  // 如果最后一行有内容，自动添加新行
  const lastRow = rows.value[rows.value.length - 1]
  if (lastRow.key || lastRow.value) {
    addRow()
  }
}

const addRow = () => {
  rows.value.push({
    enabled: true,
    key: '',
    value: '',
    description: '',
    type: 'text',
    file: null
  })
}

const removeRow = (index) => {
  if (rows.value.length > 1) {
    rows.value.splice(index, 1)
    updateValue()
  }
}

const handleFileChange = (index, file) => {
  rows.value[index].file = file
  rows.value[index].value = file.name
  updateValue()
}

// 监听props.modelValue变化
watch(
  () => props.modelValue,
  () => {
    initializeRows()
  },
  { immediate: true }
)

// 暴露rows供父组件访问
defineExpose({
  rows
})
</script>

<style scoped>
.key-value-editor {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: white;
}

.header {
  display: flex;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  padding: 8px;
  font-weight: 500;
  font-size: 12px;
  color: #606266;
}

.rows {
  max-height: 300px;
  overflow-y: auto;
}

.row {
  display: flex;
  border-bottom: 1px solid #f5f7fa;
  padding: 8px;
  min-height: 40px;
  align-items: center;
}

.row:hover {
  background: #fafbfc;
}

.row.disabled {
  opacity: 0.6;
}

.column {
  display: flex;
  align-items: center;
  gap: 8px;
}

.key-column {
  width: 25%;
  min-width: 150px;
}

.value-column {
  width: 35%;
  min-width: 200px;
}

.description-column {
  width: 25%;
  min-width: 120px;
}

.action-column {
  width: 15%;
  min-width: 100px;
  justify-content: flex-end;
}

.file-name {
  font-size: 12px;
  color: #606266;
  margin-left: 8px;
}

.footer {
  padding: 8px;
  border-top: 1px solid #f5f7fa;
  background: #fafbfc;
}
</style>