import { http } from './request'

export interface FeynmanCard {
  card_id: number
  card_type: string
  preview: string
  concept: string
}

export interface FeynmanSessionStartOut {
  session_id: number
  title: string
  card_count: number
  cards: FeynmanCard[]
}

export interface FeynmanExplainResult {
  id: number
  card_id: number
  card_preview: string
  attempt: number
  user_explanation: string
  clarity_score: number | null
  simplicity_score: number | null
  accuracy_score: number | null
  overall_score: number | null
  is_stuck: boolean
  stuck_spots: string[] | null
  suggestion: string | null
  ai_feedback: string | null
}

export interface FeynmanSessionOut {
  id: number
  title: string
  status: string
  card_count: number
  explained_count: number
  stuck_count: number
  avg_clarity: number | null
  started_at: string
  ended_at: string | null
}

export const feynmanApi = {
  start(payload: { deck_id?: number; card_ids?: number[]; count?: number; title?: string }) {
    return http.post<FeynmanSessionStartOut>('/feynman/sessions', payload)
  },
  explain(sessionId: number, cardId: number, userExplanation: string) {
    return http.post<FeynmanExplainResult>(`/feynman/sessions/${sessionId}/explain`, {
      card_id: cardId,
      user_explanation: userExplanation,
    })
  },
  complete(sessionId: number, status = 'completed') {
    return http.post(`/feynman/sessions/${sessionId}/complete`, { status })
  },
  list() {
    return http.get<FeynmanSessionOut[]>('/feynman/sessions')
  },
}
