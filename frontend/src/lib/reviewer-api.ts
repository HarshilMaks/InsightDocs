import axios from 'axios'
import { API_BASE_URL, AUTH_SESSION_EXPIRED_EVENT, clearStoredAuth, getAuthToken } from './api'

const reviewerApi = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

reviewerApi.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

reviewerApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const headers = error.config?.headers
      const authorization = headers?.Authorization ?? headers?.authorization
      if (authorization) {
        clearStoredAuth()
        window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT))
      }
    }
    return Promise.reject(error)
  },
)

export type ReviewStatus = 'pending' | 'accepted' | 'rejected'
export type ReviewDecision = Exclude<ReviewStatus, 'pending'>

export interface ReviewerBoundingBox {
  x1: number
  y1: number
  x2: number
  y2: number
  page_number?: number | null
}

export interface ReviewQueueItem {
  id: string
  query_id: string
  query_text: string
  status: string
  claim_count: number
  unsupported_count: number
  unverified_count: number
  review_status: ReviewStatus
  review_version: number
  created_at: string
}

export interface ReviewQueueResponse {
  items: ReviewQueueItem[]
  total: number
}

export interface ReviewSource {
  source_number: number
  document_id?: string | null
  document_name: string
  chunk_id: string
  chunk_index: number
  page_number?: number | null
  bbox?: ReviewerBoundingBox | null
  section_title?: string | null
  chunk_type: string
  content: string
  similarity_score: number
  citation_label: string
}

export interface ReviewClaim {
  id: string
  ordinal: number
  claim_text: string
  verdict: string
  reason?: string | null
  supporting_source_numbers: number[]
  sources: ReviewSource[]
}

export interface ReviewDecisionEvent {
  id: string
  reviewer_id?: string | null
  decision: ReviewDecision
  note?: string | null
  expected_version: number
  result_version: number
  created_at: string
}

export interface ReviewDetail {
  id: string
  query_id: string
  query_text: string
  response_text?: string | null
  policy_version: string
  mode: string
  status: string
  action?: string | null
  review_status: ReviewStatus
  review_version: number
  reviewed_at?: string | null
  created_at: string
  claims: ReviewClaim[]
  decision_history: ReviewDecisionEvent[]
}

export interface CreateReviewDecisionPayload {
  decision: ReviewDecision
  expected_version: number
  note?: string
}

export async function getReviewQueue(
  reviewStatus: ReviewStatus = 'pending',
  skip = 0,
  limit = 50,
): Promise<ReviewQueueResponse> {
  const { data } = await reviewerApi.get('/evidence-gate/reviews', {
    params: { review_status: reviewStatus, skip, limit },
  })
  return data
}

export async function getReviewDetail(runId: string): Promise<ReviewDetail> {
  const { data } = await reviewerApi.get(`/evidence-gate/reviews/${encodeURIComponent(runId)}`)
  return data
}

export async function createReviewDecision(
  runId: string,
  payload: CreateReviewDecisionPayload,
): Promise<ReviewDetail> {
  const { data } = await reviewerApi.post(
    `/evidence-gate/reviews/${encodeURIComponent(runId)}/decisions`,
    payload,
  )
  return data
}

export function isStaleReviewConflict(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 409
}
