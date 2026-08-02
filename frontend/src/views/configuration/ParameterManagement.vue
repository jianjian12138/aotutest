<template>
  <BasePage title="参数管理">
    <template #actions>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon> 新增参数
      </el-button>
    </template>
    
    
    <div class="filter-container">
      <el-input
        v-model="searchQuery"
        placeholder="搜索参数键或描述"
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

    <el-table :data="parameters" style="width: 100%" v-loading="loading">
      <el-table-column prop="key" label="参数键" width="250" sortable />
      <el-table-column prop="value" label="参数值">
        <template #default="scope">
          <span class="value-truncate" :title="scope.row.value">{{ scope.row.value }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="created_at" label="创建时间" width="180" sortable>
        <template #default="scope">
          {{ formatDate(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
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
      :title="dialogType === 'create' ? '新增参数' : '编辑参数'"
      width="500px"
    >
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="参数键" prop="key">
          <el-input v-model="form.key" :disabled="dialogType === 'edit'" />
        </el-form-item>
        <el-form-item label="参数值" prop="value">
          <el-input v-model="form.value" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </span>
      </template>
    </el-dialog>

  </BasePage>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import request from '@/utils/request.js'

const loading = ref(false)
const parameters = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')

const dialogVisible = ref(false)
const dialogType = ref('create')
const formRef = ref(null)
const form = reactive({
  id: null,
  key: '',
  value: '',
  description: ''
})

const rules = {
  key: [{ required: true, message: '请输入参数键', trigger: 'blur' }],
  value: [{ required: true, message: '请输入参数值', trigger: 'blur' }]
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString()
}

const fetchParameters = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value
    }
    const response = await request.get('configuration/parameters/', { params })
    parameters.value = response.data.results
    total.value = response.data.count
  } catch (error) {
    console.error('Fetch parameters error details:', error.toJSON ? error.toJSON() : error)
    const msg = error.response?.data?.detail || error.message || '获取参数列表失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchParameters()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  fetchParameters()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchParameters()
}

const handleCreate = () => {
  dialogType.value = 'create'
  form.id = null
  form.key = ''
  form.value = ''
  form.description = ''
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogType.value = 'edit'
  form.id = row.id
  form.key = row.key
  form.value = row.value
  form.description = row.description
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确认删除该参数吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await request.delete(`configuration/parameters/${row.id}/`)
      ElMessage.success('删除成功')
      fetchParameters()
    } catch (error) {
      console.error('Delete parameter error:', error)
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
          await request.post('configuration/parameters/', form)
          ElMessage.success('创建成功')
        } else {
          await request.put(`configuration/parameters/${form.id}/`, form)
          ElMessage.success('更新成功')
        }
        dialogVisible.value = false
        fetchParameters()
      } catch (error) {
        ElMessage.error(dialogType.value === 'create' ? '创建失败' : '更新失败')
      }
    }
  })
}

onMounted(() => {
  fetchParameters()
})
</script>

<style scoped>
.parameter-management {
  padding: 20px;
}
/* 页面特定样式 */


.filter-container {
  margin-bottom: 20px;
}


.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.value-truncate {
  display: inline-block;
  max-width: 300px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>