import { http } from './request'

export interface InterviewStartResult {
  session_id: number
  cards: {
    card_id: number
    question: string
    keywords: string[]
    difficulty: number
  }[]
}

export interface ExamStartResult {
  exam_id: number
  total_count: number
  cards: {
    card_id: number
    question: string
    options: string[]
    is_multiple: boolean
  }[]
}

export interface VocabStartResult {
  mode: string
  count: number
  cards: {
    card_id: number
    word: string
    phonetic: string | null
    cn_meaning: string | null
    en_meaning: string | null
    examples: string[]
  }[]
}

export interface ExamSubmitResult {
  exam_id: number
  total: number
  correct: number
  score: number
  duration_seconds: number | null
  details: {
    card_id: number
    answer: number[]
    correct_answer: number[]
    is_correct: boolean
    explanation: string | null
    question: string
    options: string[]
  }[]
}

export interface ExamHistoryItem {
  id: number
  total_count: number
  correct_count: number
  score: number
  duration_seconds: number | null
  created_at: string
  submitted_at: string | null
}

export const practiceApi = {
  startInterview: (params?: { deck_id?: number; count?: number }) =>
    http.post<InterviewStartResult>('/practice/interview/start', null, { params }),
  evaluateInterview: (cardId: number, userAnswer: string) =>
    http.post('/practice/interview/evaluate', { card_id: cardId, user_answer: userAnswer }),
  completeInterview: (sessionId: number, scores: any[]) =>
    http.post(`/practice/interview/${sessionId}/complete`, { scores }),

  startExam: (params?: { deck_id?: number; count?: number }) =>
    http.post<ExamStartResult>('/practice/exam/start', null, { params }),
  submitExam: (examId: number, answers: { card_id: number; answer: number[] }[]) =>
    http.post<ExamSubmitResult>(`/practice/exam/${examId}/submit`, { answers }),
  listExams: () => http.get<ExamHistoryItem[]>('/practice/exams'),

  startVocab: (params?: { deck_id?: number; mode?: string; count?: number }) =>
    http.post<VocabStartResult>('/practice/vocab/start', null, { params }),

  listMistakes: (params?: { limit?: number }) =>
    http.get<MistakeItem[]>('/practice/mistakes', { params }),
}

export interface MistakeItem {
  card_id: number
  deck_id: number
  deck_name: string
  card_type: string
  front_preview: string
  reviewed_at: string
  user_answer: string | null
}
