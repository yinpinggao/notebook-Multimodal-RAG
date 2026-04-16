'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import { useTranslation } from '@/lib/hooks/use-translation'
import { vragApi } from '@/lib/api/vrag'
import { flushSSEBuffer, parseSSEChunk } from '@/lib/utils/sse'
import {
  VRAGDAG,
  VRAGImageResult,
  VRAGMemoryNode,
  VRAGSession,
  VRAGSessionDetail,
  VRAGStreamEvent
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

const EMPTY_DAG: VRAGDAG = { nodes: [], edges: [] }

function normalizeMessages(messages: VRAGSessionDetail['messages']): VRAGMessage[] {
  return messages.map((message, index) => ({
    id: message.id || `${message.type}-${index + 1}`,
    type: message.type,
    content: message.content,
    timestamp: message.timestamp || new Date().toISOString(),
  }))
}

function extractEvidenceImages(evidence: VRAGSessionDetail['evidence']): VRAGImageResult[] {
  const images: VRAGImageResult[] = []

  for (const entry of evidence) {
    if (entry.type !== 'search' || !Array.isArray(entry.images)) {
      continue
    }

    for (const image of entry.images as Array<Record<string, unknown>>) {
      images.push({
        chunk_id: String(image.chunk_id || image.id || image.image_path || ''),
        asset_id: typeof image.asset_id === 'string' ? image.asset_id : undefined,
        score: Number(image.score || 0),
        image_path: String(image.image_path || ''),
        file_url: typeof image.file_url === 'string' ? image.file_url : undefined,
        image_base64: typeof image.image_base64 === 'string' ? image.image_base64 : undefined,
        page_no: Number(image.page_no || 0),
        source_id: String(image.source_id || ''),
        summary: typeof image.summary === 'string' ? image.summary : '',
        bbox: Array.isArray(image.bbox) ? image.bbox as number[] : undefined,
      })
    }
  }

  return images
}

function getRestoredAnswer(sessionData: VRAGSessionDetail): string {
  const metadataAnswer = sessionData.session.metadata?.current_answer
  if (metadataAnswer) {
    return metadataAnswer
  }

  const lastAiMessage = [...sessionData.messages].reverse().find((message) => message.type === 'ai')
  return lastAiMessage?.content || ''
}

function appendUniqueImages(
  previous: VRAGImageResult[],
  nextImages: NonNullable<VRAGStreamEvent['top_images']>
): VRAGImageResult[] {
  const byKey = new Map(previous.map((image) => [image.chunk_id || image.image_path, image]))

  for (const image of nextImages) {
    const key = image.chunk_id || image.image_path
    byKey.set(key, {
      chunk_id: image.chunk_id || image.image_path,
      asset_id: image.asset_id,
      score: image.score || 0,
      image_path: image.image_path,
      file_url: image.file_url,
      page_no: image.page_no,
      source_id: '',
      summary: image.summary,
    })
  }

  return Array.from(byKey.values())
}

export function useVRAGChat(notebookId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<VRAGMessage[]>([])
  const [dag, setDag] = useState<VRAGDAG>(EMPTY_DAG)
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isComplete, setIsComplete] = useState(false)
  const [evidenceImages, setEvidenceImages] = useState<VRAGImageResult[]>([])
  const abortControllerRef = useRef<AbortController | null>(null)
  const autoSelectInitializedRef = useRef(false)

  const resetLocalState = useCallback(() => {
    setMessages([])
    setDag(EMPTY_DAG)
    setCurrentAnswer('')
    setIsComplete(false)
    setError(null)
    setEvidenceImages([])
  }, [])

  useEffect(() => {
    autoSelectInitializedRef.current = false
  }, [notebookId])

  const { data: sessions = [], isLoading: loadingSessions, refetch: refetchSessions } = useQuery<VRAGSession[]>({
    queryKey: ['vragSessions', notebookId],
    queryFn: () => vragApi.listSessions(notebookId),
    enabled: !!notebookId
  })

  const { data: currentSessionData, refetch: refetchSession } = useQuery<VRAGSessionDetail>({
    queryKey: ['vragSession', sessionId],
    queryFn: () => vragApi.getSession(sessionId!),
    enabled: !!sessionId
  })

  useEffect(() => {
    if (!currentSessionData || isStreaming) {
      return
    }

    setMessages(normalizeMessages(currentSessionData.messages))
    setDag(currentSessionData.memory_graph || EMPTY_DAG)
    setEvidenceImages(extractEvidenceImages(currentSessionData.evidence))
    setCurrentAnswer(getRestoredAnswer(currentSessionData))
    setIsComplete(Boolean(
      currentSessionData.session.metadata?.is_complete ?? getRestoredAnswer(currentSessionData)
    ))
    setError(currentSessionData.session.metadata?.last_error || null)
  }, [currentSessionData, isStreaming])

  useEffect(() => {
    if (autoSelectInitializedRef.current || sessionId || sessions.length === 0) {
      return
    }

    autoSelectInitializedRef.current = true
    setSessionId(sessions[0].id)
  }, [sessions, sessionId])

  const switchSession = useCallback((newSessionId: string) => {
    autoSelectInitializedRef.current = true
    setSessionId(newSessionId || null)
    resetLocalState()
  }, [resetLocalState])

  const deleteSession = useCallback(async (id: string) => {
    try {
      await vragApi.deleteSession(id)
      await queryClient.invalidateQueries({ queryKey: ['vragSessions', notebookId] })
      await queryClient.removeQueries({ queryKey: ['vragSession', id] })

      if (sessionId === id) {
        autoSelectInitializedRef.current = true
        setSessionId(null)
        resetLocalState()
      }

      toast.success(t.common.success)
    } catch (err: unknown) {
      const apiError = err as { response?: { data?: { detail?: string } }, message?: string }
      toast.error(getApiErrorMessage(apiError.response?.data?.detail || apiError.message, (key) => t(key)))
    }
  }, [sessionId, notebookId, queryClient, resetLocalState, t])

  const sendMessage = useCallback(async (
    question: string,
    sourceIds?: string[],
    maxSteps: number = 10,
    context: string = ''
  ) => {
    const userMessage: VRAGMessage = {
      id: `human-${Date.now()}`,
      type: 'human',
      content: question,
      timestamp: new Date().toISOString()
    }

    setMessages((prev) => [...prev, userMessage])
    setIsStreaming(true)
    setIsComplete(false)
    setCurrentAnswer('')
    setError(null)

    abortControllerRef.current?.abort()
    const abortController = new AbortController()
    abortControllerRef.current = abortController

    let resolvedSessionId = sessionId || null
    let sawComplete = false
    let aiMessageId: string | null = null

    try {
      const response = await vragApi.sendMessage(notebookId, {
        question,
        notebook_id: notebookId,
        source_ids: sourceIds,
        context,
        max_steps: maxSteps,
        stream: true,
        session_id: sessionId || undefined
      }, abortController.signal)

      const responseSessionId = response.headers.get('X-Session-ID')
      if (responseSessionId) {
        resolvedSessionId = responseSessionId
        setSessionId(responseSessionId)
      }

      if (!response.body) {
        throw new Error('No response body')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let sseBuffer = ''
      const nodesMap = new Map(dag.nodes.map((node) => [node.id, node]))

      const handleEvent = (data: VRAGStreamEvent) => {
        if (data.type === 'dag_update') {
          if (data.node_id && data.node_type && data.summary) {
            nodesMap.set(data.node_id, {
              id: data.node_id,
              type: data.node_type as VRAGMemoryNode['type'],
              summary: data.summary,
              parent_ids: [],
              images: (data.top_images || []).map((image) => image.file_url || image.image_path || ''),
              priority: 1.0,
              is_useful: true,
              key_insight: data.summary.slice(0, 200)
            })

            setDag((current) => ({
              nodes: Array.from(nodesMap.values()),
              edges: current.edges
            }))
          }

          if (data.top_images && data.top_images.length > 0) {
            setEvidenceImages((prev) => appendUniqueImages(prev, data.top_images!))
          }
          return
        }

        if (data.type === 'complete') {
          sawComplete = true
          const answer = data.answer || ''
          setCurrentAnswer(answer)
          setIsComplete(true)

          if (!aiMessageId) {
            aiMessageId = `ai-${Date.now()}`
            setMessages((prev) => [...prev, {
              id: aiMessageId!,
              type: 'ai',
              content: answer,
              timestamp: new Date().toISOString()
            }])
          } else {
            setMessages((prev) => prev.map((message) => (
              message.id === aiMessageId
                ? { ...message, content: answer }
                : message
            )))
          }
          return
        }

        if (data.type === 'error') {
          throw new Error(data.error || 'VRAG stream error')
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          break
        }

        const decodedChunk = decoder.decode(value, { stream: true })
        const parsed = parseSSEChunk(
          sseBuffer,
          decodedChunk,
          (payload) => JSON.parse(payload) as VRAGStreamEvent
        )
        sseBuffer = parsed.buffer
        parsed.events.forEach(handleEvent)
      }

      const tailEvents = flushSSEBuffer(
        sseBuffer,
        (payload) => JSON.parse(payload) as VRAGStreamEvent
      )
      tailEvents.forEach(handleEvent)

      if (!sawComplete) {
        throw new Error('VRAG stream ended before completion event')
      }
    } catch (err: unknown) {
      const streamError = err as DOMException & { message?: string }
      if (streamError?.name === 'AbortError') {
        setError(null)
      } else {
        console.error('VRAG error:', streamError)
        setError(streamError.message || 'Unknown error')
        toast.error(getApiErrorMessage(streamError.message || 'apiErrors.vragError', (key) => t(key)))
      }
    } finally {
      abortControllerRef.current = null
      setIsStreaming(false)

      if (resolvedSessionId) {
        await queryClient.invalidateQueries({ queryKey: ['vragSessions', notebookId] })
        await queryClient.invalidateQueries({ queryKey: ['vragSession', resolvedSessionId] })
      }
    }
  }, [notebookId, sessionId, dag.nodes, queryClient, t])

  const cancelStreaming = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setIsStreaming(false)
  }, [])

  const resetConversation = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    autoSelectInitializedRef.current = true
    setSessionId(null)
    resetLocalState()
  }, [resetLocalState])

  const getEvidenceImages = useCallback((): VRAGImageResult[] => {
    return evidenceImages
  }, [evidenceImages])

  return {
    sessions,
    currentSession: sessions.find((session) => session.id === sessionId),
    sessionId,
    messages,
    dag,
    currentAnswer,
    isStreaming,
    isComplete,
    error,
    loadingSessions,

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
