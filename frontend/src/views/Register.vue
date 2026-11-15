<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-logo">
        <i class="fa-solid fa-seedling"></i>
      </div>
      <h1 class="auth-title">开始记忆之旅</h1>
      <p class="auth-subtitle">注册 MemoMind · 让知识温柔生长</p>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleRegister"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="你的昵称" size="large">
            <template #prefix>
              <i class="fa-regular fa-user" style="color: var(--color-muted)"></i>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="your@email.com" size="large" autocomplete="email">
            <template #prefix>
              <i class="fa-regular fa-envelope" style="color: var(--color-muted)"></i>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="至少 6 位"
            size="large"
            show-password
            autocomplete="new-password"
          >
            <template #prefix>
              <i class="fa-solid fa-lock" style="color: var(--color-muted)"></i>
            </template>
          </el-input>
        </el-form-item>

        <button
          type="button"
          class="gradient-btn"
          style="width: 100%; margin-top: 16px; font-size: 15px"
          :disabled="loading"
          @click="handleRegister"
        >
          <i class="fa-solid fa-sparkles" v-if="!loading" style="margin-right: 8px"></i>
          <i class="fa-solid fa-spinner fa-spin" v-else style="margin-right: 8px"></i>
          {{ loading ? '创建中…' : '创建账号' }}
        </button>
      </el-form>

      <p class="auth-link">
        已有账号？<router-link to="/login">立即登录</router-link>
      </p>

      <div style="margin-top: 24px; padding-top: 20px; border-top: 1px solid rgba(242, 198, 208, 0.2); text-align: center">
        <span class="color-badge mint">每天温柔复习一点点</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  email: '',
  password: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '用户名 2-50 位', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码 6-128 位', trigger: 'blur' },
  ],
}

async function handleRegister() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await userStore.register({
        username: form.username,
        email: form.email,
        password: form.password,
      })
      ElMessage.success('注册成功，请登录')
      router.push({ path: '/login', query: { email: form.email } })
    } catch {
      /* 错误已拦截 */
    } finally {
      loading.value = false
    }
  })
}
</script>
