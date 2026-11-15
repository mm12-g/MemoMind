import { http } from './request'

export interface CardLinkOut {
  id: number
  card_id: number
  target_card_id: number
  relation_type: string
  relation_label: string
  note: string | null
  target_card_preview: string
}

export const associateApi = {
  list(cardId: number) {
    return http.get<CardLinkOut[]>(`/cards/${cardId}/links`)
  },
  create(cardId: number, targetCardId: number, relationType = 'similar', note?: string) {
    return http.post(`/cards/${cardId}/links`, {
      target_card_id: targetCardId,
      relation_type: relationType,
      note,
    })
  },
  delete(cardId: number, linkId: number) {
    return http.delete(`/cards/${cardId}/links/${linkId}`)
  },
}
