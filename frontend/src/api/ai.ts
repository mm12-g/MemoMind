import { http } from './request'

export interface SourceDocData {
  id: number
  filename: string
  file_type: string
  file_size: number
  status: string
  created_at: string
}

export interface AiTaskData {
  id: number
  task_type: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  error_message: string | null
  deck_id: number | null
  source_document_id: number | null
  created_at: string
  completed_at: string | null
  generation_counts: Record<string, number>
}

export interface AiGenerationData {
  id: number
  task_id: number
  generation_type: string
  status: 'pending' | 'approved' | 'rejected' | 'failed'
  output: Record<string, any>
  saved_card_id: number | null
  approved_at: string | null
  created_at: string
}

export const aiApi = {
  upload: (
    file: File,
    deckId?: number,
    onProgress?: (percent: number) => void,
  ) => {
    const form = new FormData()
    form.append('file', file)
    if (deckId) form.append('deck_id', String(deckId))
    return http.post<{ task_id: number; source_document_id: number; filename: string; status: string }>(
      '/ai/documents/upload',
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (onProgress && e.total) {
            onProgress(Math.round((e.loaded / e.total) * 100))
          }
        },
      },
    )
  },
  generate: (deckId: number, text: string) =>
    http.post<{ task_id: number }>(`/ai/cards/generate?deck_id=${deckId}&text=${encodeURIComponent(text)}`),
  evaluate: (question: string, referenceAnswer: string, userAnswer: string) =>
    http.post('/ai/answers/evaluate', {
      question,
      reference_answer: referenceAnswer,
      user_answer: userAnswer,
    }),
  task: (id: number) => http.get<AiTaskData>(`/ai/tasks/${id}`),
  generations: (params?: { task_id?: number; status?: string; limit?: number }) =>
    http.get<AiGenerationData[]>('/ai/generations', { params }),
  approve: (id: number) => http.post(`/ai/generations/${id}/approve`),
  bulkApprove: (ids: number[]) => http.post('/ai/generations/bulk-approve', { ids }),
  reject: (id: number) => http.delete(`/ai/generations/${id}`),
  documents: () => http.get<SourceDocData[]>('/ai/documents'),
}
