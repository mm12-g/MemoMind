import { http } from './request'

export interface DashboardData {
  due_today: number
  new_today: number
  reviewed_today: number
  mastered_count: number
  streak_days: number
  today_accuracy: number | null
}

export interface TrendItem {
  date: string
  reviewed: number
  new: number
  accuracy: number | null
}

export interface TrendData {
  days: number
  items: TrendItem[]
}

export interface DeckStat {
  deck_id: number
  name: string
  card_count: number
  learning: number
  review: number
  relearning: number
  mastered: number
  mastered_pct: number
  category: string
}

export interface WeakPoint {
  card_id: number
  deck_id: number
  deck_name: string
  card_type: string
  front_preview: string
  again_count: number
  current_stability: number | null
  state: number | null
}

export interface RetentionData {
  total_cards: number
  avg_stability: number | null
  avg_retention_1d: number | null
  avg_retention_7d: number | null
  avg_retention_30d: number | null
}

export interface ReviewStatistics {
  total_reviews: number
  unique_cards_reviewed: number
  days_active: number
  accuracy_pct: number
  rating_distribution: { Again: number; Hard: number; Good: number; Easy: number }
  avg_response_ms: number | null
}

export const analyticsApi = {
  dashboard: () => http.get<DashboardData>('/analytics/dashboard'),
  trend: (params?: { days?: number }) => http.get<TrendData>('/analytics/trend', { params }),
  decks: () => http.get<DeckStat[]>('/analytics/decks'),
  weakPoints: (params?: { limit?: number }) =>
    http.get<WeakPoint[]>('/analytics/weak-points', { params }),
  retention: () => http.get<RetentionData>('/analytics/retention'),
  reviewStats: () => http.get<ReviewStatistics>('/reviews/statistics'),
}
