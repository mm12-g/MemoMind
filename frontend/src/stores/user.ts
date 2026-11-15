import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type LoginPayload, type RegisterPayload, type TokenData } from '../api/auth'
import { userApi, type UserData } from '../api/user'

const TOKEN_KEY = 'memomind_token'
const USER_KEY = 'memomind_user'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref<UserData | null>(
    JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
  )

  const isLoggedIn = computed(() => !!token.value && !!user.value)

  // 注册
  async function register(payload: RegisterPayload) {
    const res = await authApi.register(payload)
    return res.data
  }

  // 登录
  async function login(payload: LoginPayload) {
    const res = await authApi.login(payload)
    const tokenData = res.data as TokenData
    token.value = tokenData.access_token
    localStorage.setItem(TOKEN_KEY, tokenData.access_token)
    // 登录后获取用户信息
    await fetchMe()
  }

  // 获取当前用户
  async function fetchMe() {
    const res = await userApi.getMe()
    user.value = res.data as UserData
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  // 登出
  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return {
    token,
    user,
    isLoggedIn,
    register,
    login,
    fetchMe,
    logout,
  }
})
