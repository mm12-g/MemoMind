import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'

// 统一响应结构
export interface ApiResult<T = unknown> {
  code: number
  message: string
  data: T
}

// 创建 Axios 实例
const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 请求拦截器 - 自动加 Token
request.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// 响应拦截器 - 统一错误处理
request.interceptors.response.use(
  (response: AxiosResponse<ApiResult>) => {
    const res = response.data

    // code === 0 成功
    if (res.code === 0) {
      return res as unknown as AxiosResponse<ApiResult>
    }

    // 401 未授权 → 跳转登录
    if (res.code === 401) {
      ElMessage.error(res.message || '登录已过期，请重新登录')
      const userStore = useUserStore()
      userStore.logout()
      window.location.href = '/login'
      return Promise.reject(new Error(res.message))
    }

    // 其他错误
    ElMessage.error(res.message || '请求失败')
    return Promise.reject(new Error(res.message))
  },
  (error) => {
    const msg = error?.response?.data?.message || error.message || '网络错误'
    if (error?.response?.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      const userStore = useUserStore()
      userStore.logout()
      window.location.href = '/login'
    } else {
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  },
)

// 类型化请求工具
export const http = {
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<ApiResult<T>> {
    return request.get(url, config) as unknown as Promise<ApiResult<T>>
  },
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResult<T>> {
    return request.post(url, data, config) as unknown as Promise<ApiResult<T>>
  },
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResult<T>> {
    return request.put(url, data, config) as unknown as Promise<ApiResult<T>>
  },
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<ApiResult<T>> {
    return request.delete(url, config) as unknown as Promise<ApiResult<T>>
  },
}

export default request
