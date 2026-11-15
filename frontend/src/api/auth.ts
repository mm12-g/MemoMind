import { http } from './request'

export interface RegisterPayload {
  email: string
  username: string
  password: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface TokenData {
  access_token: string
  token_type: string
  expires_in: number
}

export interface RegisterData {
  user_id: number
  email: string
  username: string
}

export const authApi = {
  register: (data: RegisterPayload) => http.post<RegisterData>('/auth/register', data),
  login: (data: LoginPayload) => http.post<TokenData>('/auth/login', data),
}
