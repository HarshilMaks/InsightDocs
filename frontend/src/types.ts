export type NavView = 'documents' | 'audit' | 'chat-history' | 'settings' | 'byok' | 'help'

export interface UserSession {
  isAuthenticated: boolean
  email: string
  name: string
  role: string
  avatar: string
}

export interface ByokConfig {
  enabled: boolean
  apiKey: string
  selectedModel: string
  connectionStatus: 'healthy' | 'error' | 'untested'
  pingMs: number
  temperature: number
  maxTokens: number
  strictness: 'conservative' | 'balanced' | 'exploratory'
  autoAuditOnUpload: boolean
}
