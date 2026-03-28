export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface User {
  id: string
  email: string
  name: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginResponse {
  token: Token
  user: User
  access_token?: string
  refresh_token?: string
  token_type: string
}

export interface RegisterPayload {
  name: string
  email: string
  password: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface StoredAuth {
  accessToken: string
  refreshToken?: string
  user: User
}

export interface DocumentResponse {
  id: string
  user_id: string
  filename: string
  file_type: string
  file_size: number
  status: TaskStatus
  created_at: string
  updated_at: string
  error_message?: string | null
}

export interface DocumentListResponse {
  documents: DocumentResponse[]
  total: number
}

export interface DocumentUploadResponse {
  success: boolean
  document_id: string
  task_id: string
  message: string
}

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
  content_preview: string
  similarity_score: number
  citation_label: string
}

export interface QueryRequest {
  query: string
  top_k?: number
  conversation_id?: string | null
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
}

export interface QueryHistoryItem {
  id: string
  conversation_id?: string | null
  turn_index?: number | null
  query: string
  response?: string | null
  response_time?: number | null
  created_at: string
}

export interface QueryHistoryResponse {
  queries: QueryHistoryItem[]
  total: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: SourceReference[]
}

export interface ThreadSummary {
  conversationId: string
  latestQuery: string
  latestResponse?: string | null
  turnCount: number
  updatedAt: string
}

export interface TaskListItem {
  id: string
  task_type: string
  status: TaskStatus
  progress: number
  created_at: string
}

export interface TaskListResponse {
  tasks: TaskListItem[]
  total: number
}

export interface TaskStatusResponse {
  task_id: string
  status: TaskStatus
  progress: number
  result?: Record<string, unknown> | null
  error?: string | null
}

export type GeminiHealthStatus =
  | 'missing'
  | 'healthy'
  | 'degraded'
  | 'rate_limited'
  | 'invalid'
  | 'expired'
  | 'unsupported'
  | 'unknown'

export type GeminiModelStatus = 'primary' | 'fallback' | 'unavailable'

export interface ByokStatus {
  byok_enabled: boolean
  has_api_key: boolean
  user_id: string
  email: string
  status: GeminiHealthStatus
  model_status: GeminiModelStatus
  message: string
  active_model?: string | null
  fallback_models: string[]
  available_models: string[]
  checked_at?: string | null
}

export interface ByokSettingsPayload {
  enabled: boolean
}

export interface ApiKeyPayload {
  api_key: string
}

export interface ApiMessageResponse {
  message: string
}

export interface ApiKeyResponse {
  message: string
  byok_enabled: boolean
  status: GeminiHealthStatus
  model_status: GeminiModelStatus
  active_model?: string | null
  fallback_models: string[]
  available_models: string[]
  checked_at?: string | null
}

export interface DocumentSummaryResponse {
  document_id: string
  summary: string
}

export interface DocumentQuizResponse {
  document_id: string
  quiz: unknown
}

export interface DocumentMindmapResponse {
  document_id: string
  mindmap: unknown
}

export interface WorkspaceOutletContext {
  documents: DocumentResponse[]
  threads: ThreadSummary[]
  documentsLoading: boolean
  threadsLoading: boolean
}

export type WorkspaceTab = 'ask' | 'summary' | 'quiz' | 'mindmap'
