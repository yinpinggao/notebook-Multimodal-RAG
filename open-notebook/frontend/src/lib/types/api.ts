export interface NotebookResponse {
  id: string
  name: string
  description: string
  archived: boolean
  created: string
  updated: string
  source_count: number
  note_count: number
}

export interface NoteResponse {
  id: string
  title: string | null
  content: string | null
  note_type: string | null
  created: string
  updated: string
}

export interface SourceListResponse {
  id: string
  title: string | null
  topics?: string[]                  // Make optional to match Python API
  asset: {
    file_path?: string
    url?: string
  } | null
  embedded: boolean
  embedded_chunks: number            // ADD: From Python API
  insights_count: number
  created: string
  updated: string
  file_available?: boolean
  // ADD: Async processing fields from Python API
  command_id?: string
  status?: string
  processing_info?: Record<string, unknown>
  visual_index_status?: 'not_indexed' | 'queued' | 'running' | 'completed' | 'failed' | string | null
  visual_asset_count?: number
  visual_last_indexed_at?: string | null
  visual_index_command_id?: string | null
}

export interface SourceDetailResponse extends SourceListResponse {
  full_text: string
  notebooks?: string[]  // List of notebook IDs this source is linked to
}

export type SourceResponse = SourceDetailResponse

export interface SourceStatusResponse {
  status?: string
  message: string
  processing_info?: Record<string, unknown>
  command_id?: string
}

export interface SettingsResponse {
  default_content_processing_engine_doc?: string
  default_content_processing_engine_url?: string
  default_embedding_option?: string
  auto_delete_files?: string
  youtube_preferred_languages?: string[]
}

export interface CreateNotebookRequest {
  name: string
  description?: string
}

export interface UpdateNotebookRequest {
  name?: string
  description?: string
  archived?: boolean
}

export interface NotebookDeletePreview {
  notebook_id: string
  notebook_name: string
  note_count: number
  exclusive_source_count: number
  shared_source_count: number
}

export interface NotebookDeleteResponse {
  message: string
  deleted_notes: number
  deleted_sources: number
  unlinked_sources: number
}

export interface CreateNoteRequest {
  title?: string
  content: string
  note_type?: string
  notebook_id?: string
}

export interface CreateSourceRequest {
  // Backward compatibility: support old single notebook_id
  notebook_id?: string
  // New multi-notebook support
  notebooks?: string[]
  // Required fields
  type: 'link' | 'upload' | 'text'
  url?: string
  file_path?: string
  content?: string
  title?: string
  transformations?: string[]
  embed?: boolean
  delete_source?: boolean
  // New async processing support
  async_processing?: boolean
}

export interface UpdateNoteRequest {
  title?: string
  content?: string
  note_type?: string
}

export interface UpdateSourceRequest {
  title?: string
  type?: 'link' | 'upload' | 'text'
  url?: string
  content?: string
}

export interface APIError {
  detail: string
}

// Source Chat Types
// Base session interface with common fields
export interface BaseChatSession {
  id: string
  title: string
  created: string
  updated: string
  message_count?: number
  model_override?: string | null
}

export interface SourceChatSession extends BaseChatSession {
  source_id: string
  model_override?: string
}

export interface SourceChatMessage {
  id: string
  type: 'human' | 'ai'
  content: string
  timestamp?: string
}

export interface SourceChatContextIndicator {
  sources: string[]
  insights: string[]
  notes: string[]
}

export interface SourceChatSessionWithMessages extends SourceChatSession {
  messages: SourceChatMessage[]
  context_indicators?: SourceChatContextIndicator
}

export interface CreateSourceChatSessionRequest {
  source_id: string
  title?: string
  model_override?: string
}

export interface UpdateSourceChatSessionRequest {
  title?: string
  model_override?: string
}

export interface SendMessageRequest {
  message: string
  model_override?: string
}

export interface SourceChatStreamEvent {
  type: 'user_message' | 'ai_message' | 'context_indicators' | 'complete' | 'error'
  content?: string
  data?: unknown
  message?: string
  timestamp?: string
}

// Notebook Chat Types
export interface NotebookChatSession extends BaseChatSession {
  notebook_id: string
}

export interface NotebookChatMessage {
  id: string
  type: 'human' | 'ai'
  content: string
  timestamp?: string
}

export interface NotebookChatSessionWithMessages extends NotebookChatSession {
  messages: NotebookChatMessage[]
}

export interface CreateNotebookChatSessionRequest {
  notebook_id: string
  title?: string
  model_override?: string
}

export interface UpdateNotebookChatSessionRequest {
  title?: string
  model_override?: string | null
}

export interface SendNotebookChatMessageRequest {
  session_id: string
  message: string
  context: {
    sources: Array<Record<string, unknown>>
    notes: Array<Record<string, unknown>>
  }
  model_override?: string
}

export interface BuildContextRequest {
  notebook_id: string
  context_config: {
    sources: Record<string, string>
    notes: Record<string, string>
  }
}

export interface BuildContextResponse {
  context: {
    sources: Array<Record<string, unknown>>
    notes: Array<Record<string, unknown>>
  }
  token_count: number
  char_count: number
}

// --- VRAG (Vision RAG) types ---

export interface VRAGSession {
  id: string
  notebook_id: string
  title?: string
  created: string
  updated: string
  metadata?: VRAGSessionMetadata
}

export interface VRAGSessionMetadata {
  title?: string
  last_question?: string
  current_answer?: string
  last_answer_preview?: string
  is_complete?: boolean
  total_steps?: number
  last_error?: string | null
}

export interface VRAGSessionDetail {
  session: VRAGSession
  memory_graph: VRAGDAG | null
  evidence: Array<Record<string, unknown>>
  messages: Array<{
    id: string
    type: 'human' | 'ai'
    content: string
    timestamp?: string
  }>
}

export interface VRAGMemoryNode {
  id: string
  type: 'search' | 'bbox_crop' | 'summarize' | 'answer'
  summary: string
  parent_ids: string[]
  images: string[]
  priority: number
  is_useful: boolean
  key_insight: string
}

export interface VRAGDAG {
  nodes: VRAGMemoryNode[]
  edges: Array<{ source: string; target: string; relation: string }>
  root?: string
}

export interface VRAGStreamEvent {
  type: 'dag_update' | 'complete' | 'error'
  node?: string
  node_id?: string
  node_type?: string
  summary?: string
  dag_updates?: Array<{
    node_id: string
    node_type: string
    summary: string
  }>
  answer?: string
  error?: string
  // Image data for the current node (lightweight, from dag_update)
  top_images?: Array<{
    chunk_id?: string
    asset_id?: string
    file_url?: string
    image_path: string
    page_no: number
    score?: number
    summary: string
  }>
}

export interface VRAGSearchResult {
  images: VRAGImageResult[]
  texts: VRAGTextResult[]
  total_image_hits: number
  total_text_hits: number
}

export interface VRAGImageResult {
  chunk_id: string
  asset_id?: string
  score: number
  image_path: string
  file_url?: string
  image_base64?: string
  page_no: number
  source_id: string
  summary?: string
  bbox?: number[]
}

export interface VRAGTextResult {
  chunk_id: string
  score: number
  text: string
  page_no: number
  source_id: string
}

export interface VRAGIndexResult {
  source_id: string
  command_id?: string
  status?: 'queued' | 'running' | 'completed' | 'failed' | string
  indexing_result?: {
    total: number
    indexed: number
    skipped: number
    errors: number
  }
  rebuild_result?: {
    total: number
    rebuilt: number
    errors: number
  }
}

export interface CreateVRAGChatRequest {
  question: string
  notebook_id: string
  source_ids?: string[]
  context?: string
  session_id?: string
  max_steps?: number
  stream?: boolean
}

export interface SearchVRAGRequest {
  query: string
  source_ids?: string[]
  image_top_k?: number
  text_top_k?: number
  include_image_base64?: boolean
}
