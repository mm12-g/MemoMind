import { http } from './request'

export interface UserData {
  id: number
  email: string
  username: string
  status: string
  created_at: string
}

export interface UpdateUserPayload {
  username?: string
  email?: string
  password?: string
}

export const userApi = {
  getMe: () => http.get<UserData>('/users/me'),
  updateMe: (data: UpdateUserPayload) => http.put<UserData>('/users/me', data),
}
