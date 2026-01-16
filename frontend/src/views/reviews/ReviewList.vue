<template>
  <div class="review-list">
    <div class="header">
      <h1>用例评审</h1>
      <div class="header-actions">
        <el-button type="primary" @click="createReview">
          <el-icon><Plus /></el-icon>
          创建评审
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters">
        <el-form-item label="项目">
          <el-select v-model="filters.project" placeholder="请选择项目" clearable @change="fetchReviews" style="width: 200px;">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="请选择状态" clearable @change="fetchReviews" style="width: 150px;">
            <el-option label="待评审" value="pending" />
            <el-option label="评审中" value="in_progress" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="评审人">
          <el-select v-model="filters.reviewer" placeholder="请选择评审人" clearable @change="fetchReviews" style="width: 180px;">
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="applyFilters">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table 
      :data="reviews" 
      v-loading="loading"
      style="width: 100%"
    >
      <el-table-column prop="title" label="评审标题" min-width="200" show-overflow-tooltip />
      <el-table-column label="关联项目" width="200">
        <template #default="{ row }">
          <span v-if="row.projects && row.projects.length > 0">
            {{ row.projects.map(p => p.name).join(', ') }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="评审状态" width="120">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="优先级" width="100">
        <template #default="{ row }">
          <el-tag :class="`priority-tag ${row.priority}`">{{ getPriorityText(row.priority) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="creator.username" label="创建人" width="120" />
      <el-table-column label="用例数量" width="100">
        <template #default="{ row }">
          {{ row.testcases?.length || 0 }}
        </template>
      </el-table-column>
      <el-table-column label="评审进度" width="120">
        <template #default="{ row }">
          <el-progress 
            :percentage="getReviewProgress(row)" 
            :color="getProgressColor(row)"
            :stroke-width="6"
          />
        </template>
      </el-table-column>
      <el-table-column prop="deadline" label="截止时间" width="160">
        <template #default="{ row }">
          {{ row.deadline ? formatDate(row.deadline) : '无' }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="viewReview(row.id)">详情</el-button>
          <el-button v-if="canReview(row)" size="small" type="success" @click="submitReview(row)">评审</el-button>
          <el-button v-if="canEdit(row)" size="small" type="warning" @click="editReview(row.id)">编辑</el-button>
          <el-button 
            v-if="canDelete(row)"
            size="small" 
            type="danger"
            @click="deleteReview(row.id)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 评审对话框 -->
    <el-dialog v-model="reviewDialogVisible" title="提交评审" width="600px">
      <el-form :model="reviewForm" label-width="80px">
        <el-form-item label="评审结果" required>
          <el-radio-group v-model="reviewForm.status">
            <el-radio-button label="approved">通过</el-radio-button>
            <el-radio-button label="rejected">拒绝</el-radio-button>
            <el-radio-button label="abstained">弃权</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="评审意见">
          <el-input
            v-model="reviewForm.comment"
            type="textarea"
            :rows="4"
            placeholder="请输入评审意见"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSubmitReview">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const reviews = ref([])
const projects = ref([])
const users = ref([])
const loading = ref(false)
const reviewDialogVisible = ref(false)
const currentReview = ref(null)

const filters = reactive({
  project: '',
  status: '',
  reviewer: ''
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const reviewForm = reactive({
  status: 'approved',
  comment: ''
})

const fetchReviews = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.size,
      ...filters
    }
    Object.keys(params).forEach(key => params[key] === '' && delete params[key])
    
    const response = await api.get('/reviews/reviews/', { params })
    reviews.value = response.data.results
    pagination.total = response.data.count
  } catch (error) {
    ElMessage.error('获取评审列表失败')
  } finally {
    loading.value = false
  }
}

const applyFilters = () => {
  pagination.page = 1
  fetchReviews()
}

const resetFilters = () => {
  filters.project = ''
  filters.status = ''
  filters.reviewer = ''
  pagination.page = 1
  fetchReviews()
}

const handleSizeChange = (val) => {
  pagination.size = val
  pagination.page = 1
  fetchReviews()
}

const handleCurrentChange = (val) => {
  pagination.page = val
  fetchReviews()
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || response.data || []
  } catch (error) {
    console.error('获取项目列表失败:', error)
  }
}

const fetchUsers = async () => {
  try {
    const response = await api.get('/auth/users/')
    users.value = response.data.results || response.data || []
  } catch (error) {
    console.error('获取用户列表失败:', error)
  }
}

const createReview = () => {
  router.push('/ai-generation/reviews/create')
}

const viewReview = (id) => {
  router.push(`/ai-generation/reviews/${id}`)
}

const editReview = (id) => {
  router.push(`/ai-generation/reviews/${id}/edit`)
}

const submitReview = (review) => {
  currentReview.value = review
  reviewForm.status = 'approved'
  reviewForm.comment = ''
  reviewDialogVisible.value = true
}

const confirmSubmitReview = async () => {
  try {
    await api.post(`/reviews/reviews/${currentReview.value.id}/submit_review/`, reviewForm)
    ElMessage.success('评审提交成功')
    reviewDialogVisible.value = false
    fetchReviews()
  } catch (error) {
    ElMessage.error('评审提交失败')
  }
}

const deleteReview = async (id) => {
  try {
    await api.delete(`/reviews/reviews/${id}/`)
    ElMessage.success('删除成功')
    fetchReviews()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const getStatusType = (status) => {
  const typeMap = {
    pending: 'warning',
    in_progress: 'primary',
    approved: 'success',
    rejected: 'danger',
    cancelled: 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    pending: '待评审',
    in_progress: '评审中',
    approved: '已通过',
    rejected: '已拒绝',
    cancelled: '已取消'
  }
  return textMap[status] || status
}

const getPriorityText = (priority) => {
  const textMap = {
    low: '低',
    medium: '中',
    high: '高',
    urgent: '紧急'
  }
  return textMap[priority] || priority
}

const getReviewProgress = (review) => {
  const assignments = review.assignments || []
  if (assignments.length === 0) return 0
  
  const completedCount = assignments.filter(a => a.status !== 'pending').length
  return Math.round((completedCount / assignments.length) * 100)
}

const getProgressColor = (review) => {
  const progress = getReviewProgress(review)
  if (progress === 100) return '#67c23a'
  if (progress >= 50) return '#e6a23c'
  return '#f56c6c'
}

const canReview = (review) => {
  return review.assignments?.some(a => a.reviewer.id === userStore.user?.id && a.status === 'pending')
}

const canEdit = (review) => {
  return review.creator.id === userStore.user?.id && ['pending', 'in_progress'].includes(review.status)
}

const canDelete = (review) => {
  return review.creator.id === userStore.user?.id && review.status === 'pending'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

onMounted(() => {
  fetchReviews()
  fetchProjects()
  fetchUsers()
})
</script>

<style scoped>
.review-list {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-bar {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 4px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.priority-tag {
  &.low { color: #67c23a; }
  &.medium { color: #e6a23c; }
  &.high { color: #f56c6c; }
  &.urgent { color: #f56c6c; font-weight: bold; }
}
</style>