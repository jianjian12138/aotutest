<template>
  <BasePage title="Agent 技能库配置">
    <template #actions>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon> 新增技能
      </el-button>
    </template>

    <div class="main-content">
      <div class="card-container">
        <p class="description-text">管理 AI Agent 动态挂载的 Python 脚本工具箱</p>

        <el-table :data="skills" style="width: 100%; flex: 1;" v-loading="loading">
        <el-table-column prop="name" label="技能标识 (英)" width="150" />
        <el-table-column prop="display_name" label="展示名称" width="180" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-popconfirm title="确定要删除吗？" @confirm="handleDelete(row)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </div>

    <el-dialog :title="isEdit ? '编辑技能' : '新增技能'" v-model="dialogVisible" width="60%">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="技能标识" prop="name">
          <el-input v-model="form.name" placeholder="如: web_testing_skill" />
        </el-form-item>
        <el-form-item label="展示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="中文展示名" />
        </el-form-item>
        <el-form-item label="大模型描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="告诉大模型什么时候该调用它" />
        </el-form-item>
        <el-form-item label="Python执行代码" prop="executor_code">
          <el-input v-model="form.executor_code" type="textarea" :rows="8" class="code-font" placeholder="# def run(**kwargs):\n#   print(kwargs)\n#   return {'success': True}" />
        </el-form-item>
        <el-form-item label="启用状态" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </BasePage>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '@/utils/request'

const skills = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const form = reactive({
  id: null,
  name: '',
  display_name: '',
  description: '',
  executor_code: '',
  is_active: true
})

const rules = {
  name: [{ required: true, message: '请输入标识', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  description: [{ required: true, message: '请输入描述', trigger: 'blur' }]
}

const fetchSkills = async () => {
  loading.value = true
  try {
    const res = await request.get('assistant/config/agent-skills/')
    skills.value = res.data || res
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  Object.assign(form, { id: null, name: '', display_name: '', description: '', executor_code: '', is_active: true })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await request.delete(`assistant/config/agent-skills/${row.id}/`)
    ElMessage.success('删除成功')
    fetchSkills()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (isEdit.value) {
          await request.put(`assistant/config/agent-skills/${form.id}/`, form)
          ElMessage.success('更新成功')
        } else {
          await request.post('assistant/config/agent-skills/', form)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchSkills()
      } catch (error) {
        ElMessage.error('保存失败')
      }
    }
  })
}

onMounted(() => {
  fetchSkills()
})
</script>

<style scoped lang="scss">
.main-content {
  flex: 1;
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-container {
  flex: 1;
  background: #fff;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  padding: 24px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);

  :deep(.el-table) {
    flex: 1;
    overflow-y: auto;
  }
}

.description-text {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.code-font {
  font-family: monospace;
}
</style>
