export type DocumentType = 'pdf' | 'docx' | 'zip' | 'txt' | 'xlsx';

export type DocumentStatus = 'Completed' | 'Processing' | 'Pending' | 'Flagged';

export interface DocumentHighlight {
  id: string;
  label: string;
  text: string;
  type: 'claim' | 'flagged' | 'stat';
  claimId?: string;
}

export interface DocumentPage {
  pageNumber: number;
  title: string;
  content: string;
  highlights?: DocumentHighlight[];
  hasChart?: boolean;
  chartType?: 'growth' | 'arr' | 'expenses';
}

export interface DocumentItem {
  id: string;
  name: string;
  typeLabel: string;
  type: DocumentType;
  size: string;
  status: DocumentStatus;
  uploadDate: string;
  pages: number;
  claimsCount: number;
  flaggedCount: number;
  contentSummary: string;
  documentPages: DocumentPage[];
}

export interface Citation {
  source: string;
  page: number;
  ref: string;
}

export interface AuditClaim {
  id: string;
  title: string;
  content: string;
  status: 'SUPPORTED' | 'FLAGGED' | 'UNVERIFIED';
  flagReason?: string;
  confidence: number;
  citations: Citation[];
}

export interface VerifiedSource {
  id: string;
  label: string;
  docName: string;
  confidence?: string;
  page?: number;
}

export interface AuditAnalysis {
  summary: string;
  claims: AuditClaim[];
  verifiedSources: VerifiedSource[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  analysisResult?: AuditAnalysis;
}

export interface AuditSession {
  id: string;
  documentId: string;
  documentName: string;
  title: string;
  date: string;
  messagesCount: number;
  verifiedCount: number;
  flaggedCount: number;
  summary: string;
  messages: ChatMessage[];
}

export interface ByokConfig {
  enabled: boolean;
  apiKey: string;
  selectedModel: string;
  connectionStatus: 'healthy' | 'error' | 'untested';
  pingMs: number;
  temperature: number;
  maxTokens: number;
  strictness: 'conservative' | 'balanced' | 'exploratory';
  autoAuditOnUpload: boolean;
}

export interface UserSession {
  isAuthenticated: boolean;
  email: string;
  name: string;
  role: string;
  avatar: string;
}

export type NavView = 'documents' | 'audit' | 'chat-history' | 'settings' | 'byok' | 'help' | 'auth';
