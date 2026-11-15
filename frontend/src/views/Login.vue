<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-logo">
        <i class="fa-regular fa-lightbulb"></i>
      </div>
      <h1 class="auth-title">欢迎回来</h1>
      <p class="auth-subtitle">AI 温柔记忆平台 · 登录 MemoMind</p>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="form.email"
            placeholder="your@email.com"
            size="large"
            autocomplete="email"
          >
            <template #prefix>
              <i class="fa-regular fa-envelope" style="color: var(--color-muted)"></i>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
            autocomplete="current-password"
            @keyup.enter="handleLogin"
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
          @click="handleLogin"
        >
          <i class="fa-solid fa-right-to-bracket" v-if="!loading" style="margin-right: 8px"></i>
          <i class="fa-solid fa-spinner fa-spin" v-else style="margin-right: 8px"></i>
          {{ loading ? '登录中…' : '登录' }}
        </button>
      </el-form>

      <p class="auth-link">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </p>

      <div style="margin-top: 24px; padding-top: 20px; border-top: 1px solid rgba(242, 198, 208, 0.2); text-align: center">
        <span class="color-badge rose">温柔记忆每一天</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '../stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  email: '',
  password: '',
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await userStore.login({ email: form.email, password: form.password })
      ElMessage.success('登录成功')
      const redirect = (route.query.redirect as string) || '/dashboard'
      router.push(redirect)
    } catch {
      /* 错误由拦截器展示 */
    } finally {
      loading.value = false
    }
  })
}
</script>
