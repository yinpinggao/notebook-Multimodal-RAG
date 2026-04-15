'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import { useTranslation } from '@/lib/hooks/use-translation'
import { vragApi } from '@/lib/api/vrag'
import {
  VRAGSession,
  VRAGDAG,
  VRAGStreamEvent,
  VRAGMemoryNode,
  VRAGImageResult
} from '@/lib/types/api'

export interface VRAGMessage {
  id: string
  type: 'human' | 'ai'
  content: string
  timestamp: string
}

export interface VRAGState {
  messages: VRAGMessage[]
  dag: VRAGDAG
  currentAnswer: string
  isComplete: boolean
  isStreaming: boolean
  error: string | null
  sessionId: string | null
}

export function useVRAGChat(notebookId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<VRAGMessage[]>([])
  const [dag, setDag] = useState<VRAGDAG>({ nodes: [], edges: [] })
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isComplete, setIsComplete] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Fetch sessions
  const { data: sessions = [], isLoading: loadingSessions, refetch: refetchSessions } = useQuery<VRAGSession[]>({
    queryKey: ['vragSessions', notebookId],
    queryFn: () => vragApi.listSessions(notebookId),
    enabled: !!notebookId
  })

  // Fetch current session with full state
  const { data: currentSessionData, refetch: refetchSession } = useQuery({
    queryKey: ['vragSession', sessionId],
    queryFn: () => vragApi.getSession(sessionId!),
    enabled: !!sessionId
  })

  // Restore DAG from loaded session
  useEffect(() => {
    if (currentSessionData?.memory_graph) {
      setDag(currentSessionData.memory_graph)
    }
  }, [currentSessionData])

  // Auto-select most recent session when sessions are loaded
  useEffect(() => {
    if (sessions.length > 0 && !sessionId) {
      const mostRecentSession = sessions[0]
      setSessionId(mostRecentSession.id)
    }
  }, [sessions, sessionId])

  // Switch session
  const switchSession = useCallback((newSessionId: string) => {
    setSessionId(newSessionId)
    setMessages([])
    setDag({ nodes: [], edges: [] })
    setCurrentAnswer('')
    setIsComplete(false)
    setError(null)
  }, [])

  // Delete session
  const deleteSession = useCallback(async (id: string) => {
    try {
      await vragApi.deleteSession(id)
      queryClient.invalidateQueries({ queryKey: ['vragSessions', notebookId] })
      if (sessionId === id) {
        setSessionId(null)
        setMessages([])
        setDag({ nodes: [], edges: [] })
        setCurrentAnswer('')
        setIsComplete(false)
        setError(null)
      }
      toast.success(t.common.success)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }, message?: string }
      toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key)))
    }
  }, [sessionId, notebookId, queryClient, t])

  // Send message with streaming
  const sendMessage = useCallback(async (
    question: string,
    sourceIds?: string[],
    maxSteps: number = 10,
    context: string = ''
  ) => {
    // Add user message optimistically
    const userMessage: VRAGMessage = {
      id: `temp-${Date.now()}`,
      type: 'human',
      content: question,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    setIsStreaming(true)
    setIsComplete(false)
    setCurrentAnswer('')
    setError(null)
    setDag({ nodes: [], edges: [] })

    try {
      const requestSessionId = sessionId || undefined
      const response = await vragApi.sendMessage(notebookId, {
        question,
        notebook_id: notebookId,
        source_ids: sourceIds,
        context,
        max_steps: maxSteps,
        stream: true,
        session_id: requestSessionId
      })

      if (!response.body) {
        throw new Error('No response body')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let aiMessage: VRAGMessage | null = null
      const nodesMap = new Map<string, VRAGMemoryNode>()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: VRAGStreamEvent = JSON.parse(line.slice(6))

              if (data.type === 'dag_update') {
                // Each dag_update event contains a single node update at top level
                // Backend sends: {type: "dag_update", node: "search_action", node_id: "...", node_type: "search", summary: "..."}
                if (data.node_id && data.node_type && data.summary) {
                  const nodeId = data.node_id || `node_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
                  const newNode: VRAGMemoryNode = {
                    id: nodeId,
                    type: data.node_type as VRAGMemoryNode['type'],
                    summary: data.summary,
                    parent_ids: [],
                    images: [],
                    priority: 1.0,
                    is_useful: true,
                    key_insight: data.summary.slice(0, 200)
                  }
                  nodesMap.set(nodeId, newNode)

                  setDag({
                    nodes: Array.from(nodesMap.values()),
                    edges: []
                  })
                }
              } else if (data.type === 'complete') {
                setCurrentAnswer(data.answer || '')
                setIsComplete(true)

                // Create AI message with final answer
                if (!aiMessage) {
                  aiMessage = {
                    id: `ai-${Date.now()}`,
                    type: 'ai',
                    content: data.answer || '',
                    timestamp: new Date().toISOString()
                  }
                  setMessages(prev => [...prev, aiMessage!])
                } else {
                  aiMessage.content = data.answer || ''
                  setMessages(prev =>
                    prev.map(msg => msg.id === aiMessage!.id ? { ...msg, content: aiMessage!.content } : msg)
                  )
                }
              } else if (data.type === 'error') {
                throw new Error(data.error || 'VRAG stream error')
              }
            } catch (e) {
              if (e instanceof SyntaxError) {
                // Silently skip malformed JSON (common with SSE)
                continue
              }
              throw e
            }
          }
        }
      }

      // Extract session ID from response headers
      const responseSessionId = response.headers.get('X-Session-ID')
      if (responseSessionId && !sessionId) {
        setSessionId(responseSessionId)
        queryClient.invalidateQueries({ queryKey: ['vragSessions', notebookId] })
      }
    } catch (err: unknown) {
      const error = err as { message?: string }
      console.error('VRAG error:', error)
      setError(error.message || 'Unknown error')
      toast.error(getApiErrorMessage(error.message || 'apiErrors.vragError', (key) => t(key)))
      // Remove optimistic messages on error
      setMessages(prev => prev.filter(msg => !msg.id.startsWith('temp-')))
    } finally {
      setIsStreaming(false)
      if (sessionId) {
        refetchSession()
      }
    }
  }, [notebookId, sessionId, queryClient, refetchSession, t])

  // Cancel streaming
  const cancelStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setIsStreaming(false)
  }, [])

  // Reset conversation
  const resetConversation = useCallback(() => {
    setSessionId(null)
    setMessages([])
    setDag({ nodes: [], edges: [] })
    setCurrentAnswer('')
    setIsComplete(false)
    setError(null)
  }, [])

  // Get all retrieved images from evidence
  const getEvidenceImages = useCallback((): VRAGImageResult[] => {
    // This would be populated from collected evidence in session
    return []
  }, [])

  return {
    // State
    sessions,
    currentSession: sessions.find(s => s.id === sessionId),
    sessionId,
    messages,
    dag,
    currentAnswer,
    isStreaming,
    isComplete,
    error,
    loadingSessions,

    // Actions
    sendMessage,
    cancelStreaming,
    switchSession,
    deleteSession,
    resetConversation,
    getEvidenceImages,
    refetchSessions,
    refetchSession
  }
}