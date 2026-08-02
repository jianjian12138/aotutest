<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑测试用例' : '新建测试用例'"
    width="800px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="100px"
      label-position="top"
    >
      <el-form-item label="用例名称" prop="name">
        <el-input
          v-model="formData.name"
          placeholder="请输入测试用例名称"
          clearable
          maxlength="200"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="用例描述" prop="description">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="4"
          placeholder="请输入测试用例描述（可选）"
          maxlength="1000"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="优先级" prop="priority">
        <el-select v-model="formData.priority" placeholder="请选择优先级" style="width: 100%">
          <el-option label="高" value="high" />
          <el-option label="中" value="medium" />
          <el-option label="低" value="low" />
        </el-select>
      </el-form-item>

      <el-form-item label="所属项目" prop="project">
        <el-select
          v-model="formData.project"
          placeholder="请选择项目"
          style="width: 100%"
          :disabled="isEdit"
        >
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="submitting">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  isEdit: {
    type: Boolean,
    default: false
  },
  testCaseData: {
    type: Object,
    default: () => ({})
  },
  projects: {
    type: Array,
    default: () => []
  },
  projectId: {
    type: Number,
    default: null
  }
})

// Emits
const emit = defineEmits(['update:visible', 'submit'])

// State
const formRef = ref(null)
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})
const submitting = ref(false)

// Form Data
const formData = reactive({
  name: '',
  description: '',
  priority: 'medium',
  project: null
})

// Form Rules
const formRules = {
  name: [
    { required: true, message: '请输入用例名称', trigger: 'blur' },
    { min: 2, max: 200, message: '长度在 2 到 200 个字符', trigger: 'blur' }
  ],
  priority: [
    { required: true, message: '请选择优先级', trigger: 'change' }
  ],
  project: [
    { required: true, message: '请选择项目', trigger: 'change' }
  ]
}

// Watch
watch(() => props.testCaseData, (newVal) => {
  if (props.isEdit && newVal && Object.keys(newVal).length > 0) {
    Object.assign(formData, {
      name: newVal.name || '',
      description: newVal.description || '',
      priority: newVal.priority || 'medium',
      project: newVal.project
    })
  }
}, { immediate: true, deep: true })

watch(() => props.projectId, (newVal) => {
  if (!props.isEdit && newVal) {
    formData.project = newVal
  }
}, { immediate: true })

// Methods
const handleClose = () => {
  formRef.value?.resetFields()
  emit('update:visible', false)
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitting.value = true
    
    const submitData = {
      ...formData,
      project: formData.project || props.projectId
    }
    
    emit('submit', submitData)
    dialogVisible = false
  } catch (error) {
    console.error('表单验证失败:', error)
  } finally {
    submitting.value = false
  }
}

// Reset form when dialog closes
watch(dialogVisible, (newVal) => {
  if (!newVal) {
    setTimeout(() => {
      formRef.value?.resetFields()
    }, 300)
  }
})
</script>

<style scoped>
.el-form-item {
  margin-bottom: 20px;
}
</style>
