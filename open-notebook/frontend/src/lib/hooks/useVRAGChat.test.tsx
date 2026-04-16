import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor, act } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useVRAGChat } from './useVRAGChat'
import { vragApi } from '@/lib/api/vrag'

vi.mock('@/lib/api/vrag', () => ({
  vragApi: {
    listSessions: vi.fn(),
    getSession: vi.fn(),
    deleteSession: vi.fn(),
    sendMessage: vi.fn(),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useVRAGChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('restores messages, dag, answer, evidence, and completion state from a session', async () => {
    vi.mocked(vragApi.listSessions).mockResolvedValue([
      {
        id: 'session-1',
        notebook_id: 'notebook-1',
        title: 'Revenue Chat',
        created: '2024-01-01T00:00:00',
        updated: '2024-01-01T00:00:00',
      },
    ])
    vi.mocked(vragApi.getSession).mockResolvedValue({
      session: {
        id: 'session-1',
        notebook_id: 'notebook-1',
        title: 'Revenue Chat',
        created: '2024-01-01T00:00:00',
        updated: '2024-01-01T00:00:00',
        metadata: {
          current_answer: 'The chart shows revenue growth.',
          is_complete: true,
        },
      },
      memory_graph: {
        nodes: [{
          id: 'node-1',
          type: 'search',
          summary: 'Found chart',
          parent_ids: [],
          images: ['/tmp/chart.png'],
          priority: 1,
          is_useful: true,
          key_insight: 'Revenue chart',
        }],
        edges: [],
      },
      evidence: [{
        type: 'search',
        images: [{
          chunk_id: 'img-1',
          image_path: '/tmp/chart.png',
          page_no: 1,
          source_id: 'source-1',
          summary: 'Revenue chart',
        }],
      }],
      messages: [
        {
          id: 'human-1',
          type: 'human',
          content: 'What does the chart show?',
          timestamp: '2024-01-01T00:00:00',
        },
        {
          id: 'ai-2',
          type: 'ai',
          content: 'The chart shows revenue growth.',
          timestamp: '2024-01-01T00:01:00',
        },
      ],
    })

    const { result } = renderHook(() => useVRAGChat('notebook-1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.sessionId).toBe('session-1')
      expect(result.current.messages).toHaveLength(2)
    })

    expect(result.current.currentAnswer).toBe('The chart shows revenue growth.')
    expect(result.current.isComplete).toBe(true)
    expect(result.current.dag.nodes).toHaveLength(1)
    expect(result.current.getEvidenceImages()).toEqual([
      expect.objectContaining({
        chunk_id: 'img-1',
        image_path: '/tmp/chart.png',
        summary: 'Revenue chart',
      }),
    ])
  })

  it('aborts the active streaming request when cancelStreaming is called', async () => {
    vi.mocked(vragApi.listSessions).mockResolvedValue([])
    vi.mocked(vragApi.sendMessage).mockImplementation(
      async (_notebookId, _data, signal?: AbortSignal) => {
        return await new Promise((_resolve, reject) => {
          signal?.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'))
          })
        })
      }
    )

    const { result } = renderHook(() => useVRAGChat('notebook-1'), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      void result.current.sendMessage('Show me the chart')
    })

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(true)
    })

    act(() => {
      result.current.cancelStreaming()
    })

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(false)
    })

    const signal = vi.mocked(vragApi.sendMessage).mock.calls[0][2]
    expect(signal).toBeDefined()
    expect(signal?.aborted).toBe(true)
  })
})
