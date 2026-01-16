<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">个人设置</h1>
    </div>
    
    <div class="card-container">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息" name="basic">
          <el-form v-if="userStore.user" :model="userStore.user" label-width="100px">
            <el-form-item label="用户名">
              <el-input v-model="userStore.user.username" disabled />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="userStore.user.email" />
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="userStore.user.first_name" />
            </el-form-item>
            <el-form-item label="部门">
              <el-input v-model="userStore.user.department" />
            </el-form-item>
            <el-form-item label="职位">
              <el-input v-model="userStore.user.position" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary">保存</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="修改密码" name="password">
          <el-form label-width="100px">
            <el-form-item label="当前密码">
              <el-input type="password" />
            </el-form-item>
            <el-form-item label="新密码">
              <el-input type="password" />
            </el-form-item>
            <el-form-item label="确认密码">
              <el-input type="password" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const activeTab = ref('basic')
</script>