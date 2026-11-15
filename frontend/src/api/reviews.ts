import { http } from './request'

export interface DueCardData {
  card_id: number
  deck_id: number
  card_type: string
  front_content: Record<string, any>
  back_content: Record<string, any>
  explanation: string | null
  state: number
  due_at: string
  last_review_at: string | null
}

export interface ReviewSubmitPayload {
  session_id?: number | null
  rating: 1 | 2 | 3 | 4
  response_time_ms?: number | null
  answer_text?: string | null
  idempotency_key?: string | null
}

export interface ReviewSubmitResult {
  card_id: number
  new_state: number
  new_state_label: string
  next_due_at: string
  scheduled_days: number | null
  elapsed_days: number | null
}

export interface AiHelpResult {
  simple_explanation: string
  analogy: string | null
  key_points: string[]
  common_misconceptions: string[]
  memory_tip: string
  error?: string
}

export const reviewApi = {
  due: (params?: { deck_id?: number; limit?: number }) =>
    http.get<DueCardData[]>('/reviews/due', { params }),
  start: (params?: Record<string, any>) =>
    http.post<{ session_id: number; cards: DueCardData[] }>('/reviews/start', null, { params }),
  submit: (cardId: number, data: ReviewSubmitPayload) =>
    http.post<ReviewSubmitResult>(`/reviews/submit/${cardId}`, data),
  history: (params?: { card_id?: number; limit?: number }) =>
    http.get('/reviews/history', { params }),
  aiHelp: (cardId: number) =>
    http.post<AiHelpResult>(`/reviews/ai-help/${cardId}`),
}
