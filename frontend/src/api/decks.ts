import { http } from './request'

export interface DeckData {
  id: number
  user_id: number
  name: string
  description: string | null
  category: string
  card_count: number
  created_at: string
  updated_at: string
}

export interface DeckCreatePayload {
  name: string
  description?: string
  category?: 'general' | 'interview' | 'exam' | 'vocabulary'
}

export interface DeckUpdatePayload {
  name?: string
  description?: string | null
  category?: string
}

export interface DeckListData {
  items: DeckData[]
  total: number
}

export const deckApi = {
  create: (data: DeckCreatePayload) => http.post<DeckData>('/decks', data),
  list: (params?: { category?: string; keyword?: string }) =>
    http.get<DeckListData>('/decks', { params }),
  get: (id: number) => http.get<DeckData>(`/decks/${id}`),
  update: (id: number, data: DeckUpdatePayload) =>
    http.put<DeckData>(`/decks/${id}`, data),
  remove: (id: number) => http.delete(`/decks/${id}`),
}
