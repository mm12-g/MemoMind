import { http, type ApiResult } from './request'

export interface CardData {
  id: number
  deck_id: number
  card_type: 'basic' | 'interview' | 'choice' | 'vocabulary'
  front_content: Record<string, any>
  back_content: Record<string, any>
  explanation: string | null
  source_id: number | null
  created_at: string
  updated_at: string
  tags: { id: number; name: string; color: string | null }[]
}

export interface CardCreatePayload {
  deck_id: number
  card_type: string
  front_content: Record<string, any>
  back_content: Record<string, any>
  explanation?: string | null
  tag_ids?: number[]
}

export interface CardUpdatePayload {
  card_type?: string
  front_content?: Record<string, any>
  back_content?: Record<string, any>
  explanation?: string | null
  tag_ids?: number[]
}

export interface CardListParams {
  deck_id?: number
  card_type?: string
  keyword?: string
  tag_id?: number
  page?: number
  page_size?: number
}

export interface CardListData {
  items: CardData[]
  total: number
  page: number
  page_size: number
}

export const cardApi = {
  create: (data: CardCreatePayload) => http.post<CardData>('/cards', data),
  list: (params?: CardListParams) =>
    http.get<CardListData>('/cards', { params }),
  get: (id: number) => http.get<CardData>(`/cards/${id}`),
  update: (id: number, data: CardUpdatePayload) =>
    http.put<CardData>(`/cards/${id}`, data),
  remove: (id: number) => http.delete(`/cards/${id}`),
  batchDelete: (cardIds: number[]) =>
    http.delete<{ deleted: number }>('/cards/batch', { data: { card_ids: cardIds } }),
  import: (data: { deck_id: number; cards: CardCreatePayload[] }) =>
    http.post<{ created: number }>('/cards/import', data),
}
