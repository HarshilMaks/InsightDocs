import axios, { type AxiosError } from 'axios'
import type {
  ApiKeyPayload,
  ApiKeyResponse,
  ApiMessageResponse,
  ByokSettingsPayload,
  ByokStatus,
  DocumentListResponse,
  DocumentMindmapResponse,
  DocumentQuizResponse,
  DocumentResponse,
  DocumentSummaryResponse,
  DocumentUploadResponse,
  LoginPayload,
  LoginResponse,
  QueryHistoryResponse,
  QueryRequest,
  QueryResponse,
  RegisterPayload,
  StoredAuth,
  TaskListResponse,
  TaskStatusResponse,
  User,
} from '@/types'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

const STORAGE_KEY = 'insightdocs-auth'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as StoredAuth
        if (parsed.accessToken) {
          config.headers = config.headers ?? {}
          config.headers.Authorization = `Bearer ${parsed.accessToken}`
        }
      } catch {
        window.localStorage.removeItem(STORAGE_KEY)
      }
    }
  }

  return config
})

export function getStoredAuth(): StoredAuth | null {
  if (typeof window === 'undefined') {
    return null
  }

  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (!stored) {
    return null
  }

  try {
    return JSON.parse(stored) as StoredAuth
  } catch {
    window.localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

export function persistAuth(auth: StoredAuth): void {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(auth))
}

export function clearStoredAuth(): void {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.removeItem(STORAGE_KEY)
}

export function getAuthToken(): string | null {
  return getStoredAuth()?.accessToken ?? null
}

export async function registerUser(payload: RegisterPayload): Promise<User> {
  const { data } = await api.post<User>('/auth/register', payload)
  return data
}

export async function loginUser(payload: LoginPayload): Promise<LoginResponse> {
  const body = new URLSearchParams()
  body.set('username', payload.email)
  body.set('password', payload.password)

  const { data } = await api.post<LoginResponse>('/auth/login', body, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  })

  return data
}

export async function listDocuments(): Promise<DocumentListResponse> {
  const { data } = await api.get<DocumentListResponse>('/documents/')
  return data
}

export async function getDocument(documentId: string): Promise<DocumentResponse> {
  const { data } = await api.get<DocumentResponse>(`/documents/${documentId}`)
  return data
}

export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post<DocumentUploadResponse>('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return data
}

export async function deleteDocument(documentId: string): Promise<ApiMessageResponse> {
  const { data } = await api.delete<ApiMessageResponse>(`/documents/${documentId}`)
  return data
}

export async function summarizeDocument(documentId: string): Promise<DocumentSummaryResponse> {
  const { data } = await api.post<DocumentSummaryResponse>(`/documents/${documentId}/summarize`)
  return data
}

export async function generateQuiz(documentId: string): Promise<DocumentQuizResponse> {
  const { data } = await api.post<DocumentQuizResponse>(`/documents/${documentId}/quiz`)
  return data
}

export async function generateMindmap(documentId: string): Promise<DocumentMindmapResponse> {
  const { data } = await api.post<DocumentMindmapResponse>(`/documents/${documentId}/mindmap`)
  return data
}

export async function listTasks(skip = 0, limit = 100): Promise<TaskListResponse> {
  const { data } = await api.get<TaskListResponse>('/tasks/', {
    params: {
      skip,
      limit,
    },
  })
  return data
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const { data } = await api.get<TaskStatusResponse>(`/tasks/${taskId}`)
  return data
}

export async function sendQuery(payload: QueryRequest): Promise<QueryResponse> {
  const { data } = await api.post<QueryResponse>('/query/', payload)
  return data
}

export async function getQueryHistory(conversationId?: string | null): Promise<QueryHistoryResponse> {
  const { data } = await api.get<QueryHistoryResponse>('/query/history', {
    params: conversationId ? { conversation_id: conversationId } : undefined,
  })
  return data
}

export async function getByokStatus(): Promise<ByokStatus> {
  const { data } = await api.get<ByokStatus>('/users/me/byok-status')
  return data
}

export async function saveApiKey(payload: ApiKeyPayload): Promise<ApiKeyResponse> {
  const { data } = await api.put<ApiKeyResponse>('/users/me/api-key', payload)
  return data
}

export async function removeApiKey(): Promise<ApiMessageResponse> {
  const { data } = await api.delete<ApiMessageResponse>('/users/me/api-key')
  return data
}

export async function updateByokSettings(payload: ByokSettingsPayload): Promise<ApiMessageResponse> {
  const { data } = await api.patch<ApiMessageResponse>('/users/me/byok-settings', payload)
  return data
}

export function getApiErrorMessage(error: unknown): string {
  const axiosError = error as AxiosError<{ detail?: unknown }>
  const detail = axiosError.response?.data?.detail

  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          return String((item as { msg?: string }).msg ?? '')
        }
        return ''
      })
      .filter(Boolean)
      .join(', ')
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Something went wrong. Please try again.'
}
