<template>
  <div>
    <el-card>
      <template #header>账户信息</template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户 ID">{{ userStore.user?.id }}</el-descriptions-item>
        <el-descriptions-item label="用户名">{{ userStore.user?.username }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ userStore.user?.email }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="userStore.user?.status === 'active' ? 'success' : 'danger'">
            {{ userStore.user?.status }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">{{ userStore.user?.created_at }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
</script>
