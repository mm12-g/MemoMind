import { http } from './request'

export interface GoalData {
  id: number
  user_id: number
  daily_new_limit: number
  daily_review_limit: number
  daily_minutes_goal: number
  desired_retention: number
}

export interface DailyProgress {
  goals: {
    daily_new_limit: number
    daily_review_limit: number
    daily_minutes_goal: number
  }
  actual: {
    new_today: number
    reviewed_today: number
    accuracy_pct: number
    due_today: number
  }
  progress: {
    new_pct: number
    review_pct: number
  }
}

export const goalApi = {
  get: () => http.get<GoalData>('/goals'),
  update: (data: Partial<Omit<GoalData, 'id' | 'user_id'>>) =>
    http.put<GoalData>('/goals', data),
  daily: () => http.get<DailyProgress>('/goals/daily'),
}
