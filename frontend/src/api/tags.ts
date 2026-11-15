import { http } from './request'

export interface TagData {
  id: number
  user_id: number
  name: string
  color: string | null
  created_at: string
  card_count?: number
}

export const tagApi = {
  create: (data: { name: string; color?: string }) => http.post<TagData>('/tags', data),
  list: (params?: { keyword?: string }) => http.get<TagData[]>('/tags', { params }),
  update: (id: number, data: { name?: string; color?: string }) =>
    http.put<TagData>(`/tags/${id}`, data),
  remove: (id: number) => http.delete(`/tags/${id}`),
  attach: (tagId: number, cardId: number) =>
    http.post(`/tags/${tagId}/cards/${cardId}`),
  detach: (tagId: number, cardId: number) =>
    http.delete(`/tags/${tagId}/cards/${cardId}`),
}
