<template>
  <div class="common-method-management">
    <div class="header">
      <h2>公共方法管理</h2>
      <el-button type="primary" @click="handleCreate">新增方法</el-button>
    </div>

    <div class="filter-container">
      <el-input
        v-model="searchQuery"
        placeholder="搜索方法名、关键字或描述"
        style="width: 300px;"
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button @click="handleSearch">
            <el-icon><Search /></el-icon>
          </el-button>
        </template>
      </el-input>
    </div>

    <el-table :data="methods" style="width: 100%" v-loading="loading">
      <el-table-column prop="name" label="方法名称" width="200" sortable />
      <el-table-column prop="keyword" label="调用关键字" width="180">
        <template #default="scope">
          <el-tag>{{ scope.row.keyword }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" />
      <el-table-column label="操作" width="220">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="success" @click="handleDebug(scope.row)">调试</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
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

    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'create' ? '新增公共方法' : '编辑公共方法'"
      width="600px"
    >
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="方法名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：智能点击" />
        </el-form-item>
        <el-form-item label="调用关键字" prop="keyword">
          <el-input v-model="form.keyword" placeholder="例如：$smart_click" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="代码片段" prop="code_snippet">
          <el-input 
            v-model="form.code_snippet" 
            type="textarea" 
            :rows="6" 
            placeholder="Python 代码实现"
            class="code-input"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog
      v-model="debugDialogVisible"
      title="调试公共方法"
      width="600px"
    >
      <el-form :model="debugForm" label-width="100px" ref="debugFormRef">
        <el-form-item label="参数列表">
          <div v-for="(arg, index) in debugForm.args" :key="index" class="arg-item">
            <el-input v-model="debugForm.args[index]" placeholder="请输入参数值" style="width: 200px; margin-right: 10px;" />
            <el-button type="danger" icon="Delete" circle size="small" @click="removeArg(index)" />
          </div>
          <el-button type="primary" plain size="small" @click="addArg" style="margin-top: 10px;">添加参数</el-button>
        </el-form-item>
        <el-form-item label="调试结果">
          <el-input
            v-model="debugResult"
            type="textarea"
            :rows="6"
            readonly
            class="code-input"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="debugDialogVisible = false">关闭</el-button>
          <el-button type="success" @click="handleRunDebug" :loading="debugLoading">执行</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request.js'

const loading = ref(false)
const methods = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')

const dialogVisible = ref(false)
const dialogType = ref('create')
const formRef = ref(null)
const form = reactive({
  id: null,
  name: '',
  keyword: '',
  description: '',
  code_snippet: '',
  params_schema: []
})

// 调试相关
const debugDialogVisible = ref(false)
const debugLoading = ref(false)
const debugResult = ref('')
const currentDebugMethod = ref(null)
const debugForm = reactive({
  args: []
})

const rules = {
  name: [{ required: true, message: '请输入方法名称', trigger: 'blur' }],
  keyword: [{ required: true, message: '请输入调用关键字', trigger: 'blur' }]
}

const fetchMethods = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value
    }
    const response = await request.get('configuration/common-methods/', { params })
    methods.value = response.data.results
    total.value = response.data.count
  } catch (error) {
    console.error('Fetch methods error details:', error.toJSON ? error.toJSON() : error)
    const msg = error.response?.data?.detail || error.message || '获取方法列表失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchMethods()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  fetchMethods()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchMethods()
}

const handleCreate = () => {
  dialogType.value = 'create'
  form.id = null
  form.name = ''
  form.keyword = ''
  form.description = ''
  form.code_snippet = ''
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogType.value = 'edit'
  form.id = row.id
  form.name = row.name
  form.keyword = row.keyword
  form.description = row.description
  form.code_snippet = row.code_snippet
  dialogVisible.value = true
}

const handleDebug = (row) => {
  currentDebugMethod.value = row
  debugForm.args = []
  debugResult.value = ''
  debugDialogVisible.value = true
}

const addArg = () => {
  debugForm.args.push('')
}

const removeArg = (index) => {
  debugForm.args.splice(index, 1)
}

const handleRunDebug = async () => {
  if (!currentDebugMethod.value) return
  
  debugLoading.value = true
  debugResult.value = '正在执行...'
  
  try {
    const response = await request.post(`configuration/common-methods/${currentDebugMethod.value.id}/debug/`, {
      args: debugForm.args
    })
    debugResult.value = response.data.result || response.data.message
    ElMessage.success('执行成功')
  } catch (error) {
    console.error('Debug common method error:', error)
    const errorData = error.response?.data
    if (errorData?.traceback) {
      debugResult.value = `错误: ${errorData.error}\n\n堆栈信息:\n${errorData.traceback}`
    } else {
      debugResult.value = `错误: ${errorData?.error || error.message || '执行失败'}`
    }
    ElMessage.error('执行失败')
  } finally {
    debugLoading.value = false
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确认删除该方法吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await request.delete(`configuration/common-methods/${row.id}/`)
      ElMessage.success('删除成功')
      fetchMethods()
    } catch (error) {
      console.error('Delete common method error:', error)
      const msg = error.response?.data?.error || error.response?.data?.detail || '删除失败'
      ElMessage.error(msg)
    }
  }).catch(() => {
    // 用户取消删除，不报错
  })
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (dialogType.value === 'create') {
          await request.post('configuration/common-methods/', form)
          ElMessage.success('创建成功')
        } else {
          await request.put(`configuration/common-methods/${form.id}/`, form)
          ElMessage.success('更新成功')
        }
        dialogVisible.value = false
        fetchMethods()
      } catch (error) {
        ElMessage.error(dialogType.value === 'create' ? '创建失败' : '更新失败')
      }
    }
  })
}

onMounted(() => {
  fetchMethods()
})
</script>

<style scoped>
.common-method-management {
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.filter-container {
  margin-bottom: 20px;
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.code-input {
  font-family: monospace;
}
.arg-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}
</style>
