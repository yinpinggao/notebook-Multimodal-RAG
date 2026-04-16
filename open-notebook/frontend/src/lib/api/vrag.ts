import apiClient from './client'
import {
  VRAGDAG,
  VRAGSearchResult,
  VRAGIndexResult,
  VRAGSession,
  VRAGSessionDetail,
  VRAGSessionMetadata,
  CreateVRAGChatRequest,
  SearchVRAGRequest
} from '@/lib/types/api'

export interface VRAGStreamResponse {
  body: ReadableStream<Uint8Array> | null
  headers: Headers
}

export const vragApi = {
  // VRAG Chat with streaming
  sendMessage: (_notebookId: string, data: CreateVRAGChatRequest, signal?: AbortSignal) => {
    // Get auth token using the same logic as apiClient interceptor
    let token = null
    if (typeof window !== 'undefined') {
      const authStorage = localStorage.getItem('auth-storage')
      if (authStorage) {
        try {
          const { state } = JSON.parse(authStorage)
          if (state?.token) {
            token = state.token
          }
        } catch (error) {
          console.error('Error parsing auth storage:', error)
        }
      }
    }

    const url = `/api/vrag/chat/stream`

    // Use fetch with ReadableStream for SSE
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
      body: JSON.stringify(data),
      signal
    }).then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return {
        body: response.body,
        headers: response.headers,
      } as VRAGStreamResponse
    })
  },

  // Direct multimodal search without agent
  search: async (data: SearchVRAGRequest) => {
    const response = await apiClient.post<VRAGSearchResult>('/vrag/search', data)
    return response.data
  },

  // Index a source for multimodal search
  indexSource: async (sourceId: string, sourcePath: string, sourceType: string = 'pdf', generateSummaries: boolean = true, dpi?: number) => {
    const response = await apiClient.post<VRAGIndexResult>('/vrag/index', {
      source_id: sourceId,
      source_path: sourcePath,
      source_type: sourceType,
      generate_summaries: generateSummaries,
      dpi: dpi
    })
    return response.data
  },

  // Rebuild VRAG index for a source
  rebuildIndex: async (sourceId: string, generateSummaries: boolean = true) => {
    const response = await apiClient.post<VRAGIndexResult>('/vrag/reindex', {
      source_id: sourceId,
      source_path: '',
      source_type: 'pdf',
      generate_summaries: generateSummaries
    })
    return response.data
  },

  // List VRAG sessions
  listSessions: async (notebookId?: string, limit: number = 50): Promise<VRAGSession[]> => {
    const params = new URLSearchParams()
    if (notebookId) params.append('notebook_id', notebookId)
    params.append('limit', limit.toString())
    const response = await apiClient.get<{ sessions: Record<string, unknown>[] }>(`/vrag/sessions?${params}`)
    // Transform backend field names to frontend type
    return response.data.sessions.map((s: Record<string, unknown>) => ({
      id: String(s.session_id ?? ''),
      notebook_id: String(s.notebook_id ?? ''),
      title: s.metadata && typeof s.metadata === 'object' ? (s.metadata as Record<string, unknown>).title as string : undefined,
      created: String(s.created_at ?? ''),
      updated: String(s.updated_at ?? ''),
    }))
  },

  // Get a VRAG session with full state
  getSession: async (sessionId: string) => {
    const response = await apiClient.get<{
      session: Record<string, unknown>
      memory_graph: VRAGDAG | null
      evidence: Array<Record<string, unknown>>
      messages: VRAGSessionDetail['messages']
    }>(`/vrag/sessions/${sessionId}`)
    const s = response.data.session as Record<string, unknown>
    const metadata = s.metadata && typeof s.metadata === 'object'
      ? s.metadata as VRAGSessionMetadata
      : undefined
    return {
      session: {
        id: String(s.session_id ?? ''),
        notebook_id: String(s.notebook_id ?? ''),
        title: metadata?.title,
        created: String(s.created_at ?? ''),
        updated: String(s.updated_at ?? ''),
        metadata,
      },
      memory_graph: response.data.memory_graph,
      evidence: response.data.evidence,
      messages: response.data.messages,
    } as VRAGSessionDetail
  },

  // Get the DAG graph for a VRAG session
  getGraph: async (sessionId: string) => {
    const response = await apiClient.get<VRAGDAG>(`/vrag/sessions/${sessionId}/graph`)
    return response.data
  },

  // Delete a VRAG session
  deleteSession: async (sessionId: string) => {
    const response = await apiClient.delete<{ session_id: string }>(`/vrag/sessions/${sessionId}`)
    return response.data
  }
}
