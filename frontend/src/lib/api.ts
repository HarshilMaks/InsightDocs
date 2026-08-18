import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'https://insightdocs-api-vlbl.onrender.com'

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auth persistence
export interface StoredAuth {
  accessToken: string
  user: {
    id: string
    email: string
    name: string
    role: string
    is_active: boolean
    created_at: string
    updated_at: string
  }
}

export function getStoredAuth(): StoredAuth | null {
  try {
    const raw = localStorage.getItem('insightdocs_auth')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function persistAuth(auth: StoredAuth): void {
  localStorage.setItem('insightdocs_auth', JSON.stringify(auth))
}

export function clearStoredAuth(): void {
  localStorage.removeItem('insightdocs_auth')
}

export function getAuthToken(): string | null {
  return getStoredAuth()?.accessToken ?? null
}

// ──────────────────────────────────────────────
// Auth
// ──────────────────────────────────────────────

export async function registerUser(payload: { name: string; email: string; password: string }) {
  const { data } = await api.post('/auth/register', payload)
  return data
}

export async function loginUser(payload: { email: string; password: string }) {
  const { data } = await api.post('/auth/login', payload)
  return data
}

// ──────────────────────────────────────────────
// Documents
// ──────────────────────────────────────────────

export interface DocumentResponse {
  id: string
  user_id: string
  filename: string
  file_type: string
  file_size: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  error_message?: string | null
}

export async function listDocuments(): Promise<{ documents: DocumentResponse[]; total: number }> {
  const { data } = await api.get('/documents/')
  return data
}

export async function getDocument(documentId: string): Promise<DocumentResponse> {
  const { data } = await api.get(`/documents/${documentId}`)
  return data
}

export async function uploadDocument(file: File): Promise<{ success: boolean; document_id: string; task_id: string; message: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function deleteDocument(documentId: string): Promise<{ message: string }> {
  const { data } = await api.delete(`/documents/${documentId}`)
  return data
}

export async function getDocumentFileUrl(documentId: string): Promise<{ document_id: string; url: string; expires_in: number }> {
  const { data } = await api.get(`/documents/${documentId}/file-url`)
  return data
}

export async function summarizeDocument(documentId: string): Promise<{ document_id: string; summary: string }> {
  const { data } = await api.post(`/documents/${documentId}/summarize`)
  return data
}

export async function generateQuiz(documentId: string): Promise<{ document_id: string; quiz: unknown }> {
  const { data } = await api.post(`/documents/${documentId}/quiz`)
  return data
}

export async function generateMindmap(documentId: string): Promise<{ document_id: string; mindmap: unknown }> {
  const { data } = await api.post(`/documents/${documentId}/mindmap`)
  return data
}

// ──────────────────────────────────────────────
// Query (Ask AI)
// ──────────────────────────────────────────────

export interface BoundingBox {
  x1: number
  y1: number
  x2: number
  y2: number
  page_number?: number | null
}

export interface SourceReference {
  source_number: number
  document_id: string
  document_name: string
  chunk_id: string
  chunk_index: number
  page_number?: number | null
  bbox?: BoundingBox | null
  section_title?: string | null
  chunk_type: string
  content_preview: string
  similarity_score: number
  citation_label: string
}

export interface ClaimVerification {
  claim: string
  status: 'supported' | 'unsupported' | 'unverified'
  supporting_sources: number[]
  reason?: string | null
}

export interface QueryResponse {
  answer: string
  sources: SourceReference[]
  query_id: string
  conversation_id: string
  turn_index: number
  query: string
  response_time: number
  confidence_score?: number | null
  tokens_used?: number | null
  claim_verifications?: ClaimVerification[] | null
}

export async function sendQuery(payload: {
  query: string
  top_k?: number
  conversation_id?: string
  document_id?: string
}): Promise<QueryResponse> {
  const { data } = await api.post('/query/', payload)
  return data
}

export async function getQueryHistory(conversationId?: string | null): Promise<{ queries: Array<{
  id: string
  conversation_id?: string | null
  turn_index?: number | null
  query: string
  response?: string | null
  response_time?: number | null
  created_at: string
}>; total: number }> {
  const params: Record<string, string> = {}
  if (conversationId) params.conversation_id = conversationId
  const { data } = await api.get('/query/history', { params })
  return data
}

// ──────────────────────────────────────────────
// Tasks
// ──────────────────────────────────────────────

export async function getTaskStatus(taskId: string): Promise<{
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  result?: Record<string, unknown> | null
  error?: string | null
}> {
  const { data } = await api.get(`/tasks/${taskId}`)
  return data
}

export async function listTasks(): Promise<{ tasks: Array<{
  id: string
  task_type: string
  status: string
  progress: number
  created_at: string
}>; total: number }> {
  const { data } = await api.get('/tasks/')
  return data
}

// ──────────────────────────────────────────────
// BYOK
// ──────────────────────────────────────────────

export interface ByokStatus {
  byok_enabled: boolean
  has_api_key: boolean
  user_id: string
  email: string
  status: string
  model_status: string
  message: string
  active_model?: string | null
  fallback_models: string[]
  available_models: string[]
  checked_at?: string | null
}

export async function getByokStatus(): Promise<ByokStatus> {
  const { data } = await api.get('/users/me/byok-status')
  return data
}

export async function saveApiKey(apiKey: string): Promise<{
  message: string
  byok_enabled: boolean
  status: string
  model_status: string
  active_model?: string | null
  fallback_models: string[]
  available_models: string[]
}> {
  const { data } = await api.put('/users/me/api-key', { api_key: apiKey })
  return data
}

export async function removeApiKey(): Promise<{ message: string }> {
  const { data } = await api.delete('/users/me/api-key')
  return data
}

export async function updateByokSettings(enabled: boolean): Promise<void> {
  await api.patch('/users/me/byok-settings', { enabled })
}

// ──────────────────────────────────────────────
// Error handling
// ──────────────────────────────────────────────

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.response?.data?.message || error.message
  }
  if (error instanceof Error) return error.message
  return 'An unexpected error occurred'
}
