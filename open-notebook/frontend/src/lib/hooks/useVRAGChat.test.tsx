import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor, act } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useVRAGChat } from './useVRAGChat'
import { vragApi } from '@/lib/api/vrag'
import type { VRAGSessionDetail } from '@/lib/types/api'

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
          label: '[search]\nFound chart...',
          images: [null, '/tmp/chart.png'],
          priority: 1,
          is_useful: true,
          key_insight: 'Revenue chart',
        }],
        edges: [{
          from: 'node-0',
          to: 'node-1',
        }],
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
    } as unknown as VRAGSessionDetail)

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
    expect(result.current.dag.nodes[0].summary).toBe('Found chart...')
    expect(result.current.dag.nodes[0].images).toEqual(['/tmp/chart.png'])
    expect(result.current.dag.edges).toEqual([
      {
        source: 'node-0',
        target: 'node-1',
        relation: 'depends_on',
      },
    ])
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

  it('restores the session when the stream ends before a completion event', async () => {
    vi.mocked(vragApi.listSessions).mockResolvedValue([])
    vi.mocked(vragApi.getSession).mockResolvedValue({
      session: {
        id: 'session-stream',
        notebook_id: 'notebook-1',
        title: 'Revenue Chat',
        created: '2024-01-01T00:00:00',
        updated: '2024-01-01T00:00:00',
        metadata: {
          current_answer: 'Recovered answer from persisted session state.',
          is_complete: true,
        },
      },
      memory_graph: {
        nodes: [{
          id: 'node-1',
          type: 'search',
          summary: 'Found chart',
          parent_ids: [],
          images: ['/api/visual-assets/asset-1/file'],
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
          asset_id: 'asset-1',
          file_url: '/api/visual-assets/asset-1/file',
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
          content: 'Show me the chart',
          timestamp: '2024-01-01T00:00:00',
        },
        {
          id: 'ai-2',
          type: 'ai',
          content: 'Recovered answer from persisted session state.',
          timestamp: '2024-01-01T00:01:00',
        },
      ],
    })
    vi.mocked(vragApi.sendMessage).mockResolvedValue({
      body: new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode(
              'data: {"type":"dag_update","node_id":"node-1","node_type":"search","summary":"Found chart"}\n\n'
            )
          )
          controller.close()
        },
      }),
      headers: new Headers({
        'X-Session-ID': 'session-stream',
      }),
    })

    const { result } = renderHook(() => useVRAGChat('notebook-1'), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.sendMessage('Show me the chart')
    })

    await waitFor(() => {
      expect(result.current.sessionId).toBe('session-stream')
      expect(result.current.currentAnswer).toBe('Recovered answer from persisted session state.')
      expect(result.current.isComplete).toBe(true)
      expect(result.current.error).toBeNull()
    })

    expect(vragApi.getSession).toHaveBeenCalledWith('session-stream')
    expect(result.current.getEvidenceImages()).toEqual([
      expect.objectContaining({
        chunk_id: 'img-1',
        asset_id: 'asset-1',
        file_url: '/api/visual-assets/asset-1/file',
      }),
    ])
  })

  it('consumes legacy dag stream events whose type is search instead of dag_update', async () => {
    vi.mocked(vragApi.listSessions).mockResolvedValue([])
    vi.mocked(vragApi.getSession).mockResolvedValue({
      session: {
        id: 'session-legacy',
        notebook_id: 'notebook-1',
        title: 'Legacy Session',
        created: '2024-01-01T00:00:00',
        updated: '2024-01-01T00:00:00',
        metadata: {
          current_answer: '这是最终答案。',
          is_complete: true,
        },
      },
      memory_graph: {
        nodes: [{
          id: 'search-1',
          type: 'search',
          summary: '找到 2 张图片，1 段文本',
          parent_ids: [],
          images: ['/tmp/chart.png'],
          priority: 1,
          is_useful: true,
          key_insight: 'Table VI',
        }],
        edges: [],
      },
      evidence: [{
        type: 'search',
        images: [{
          chunk_id: 'img-legacy',
          image_path: '/tmp/chart.png',
          page_no: 11,
          source_id: 'source-1',
          summary: 'Table VI',
        }],
      }],
      messages: [
        {
          id: 'human-1',
          type: 'human',
          content: '你现在可以看见什么图片？',
          timestamp: '2024-01-01T00:00:00',
        },
        {
          id: 'ai-2',
          type: 'ai',
          content: '这是最终答案。',
          timestamp: '2024-01-01T00:01:00',
        },
      ],
    } as unknown as VRAGSessionDetail)
    vi.mocked(vragApi.sendMessage).mockResolvedValue({
      body: new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode(
              'data: {"type":"search","node":"search","node_id":"search-1","node_type":"search","summary":"找到 2 张图片，1 段文本","top_images":[{"chunk_id":"img-legacy","image_path":"/tmp/chart.png","page_no":11,"summary":"Table VI"}]}\n\n'
            )
          )
          controller.enqueue(
            new TextEncoder().encode(
              'data: {"type":"complete","answer":"这是最终答案。"}\n\n'
            )
          )
          controller.close()
        },
      }),
      headers: new Headers({
        'X-Session-ID': 'session-legacy',
      }),
    })

    const { result } = renderHook(() => useVRAGChat('notebook-1'), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.sendMessage('你现在可以看见什么图片？')
    })

    await waitFor(() => {
      expect(result.current.sessionId).toBe('session-legacy')
      expect(result.current.currentAnswer).toBe('这是最终答案。')
      expect(result.current.isComplete).toBe(true)
    })

    expect(result.current.dag.nodes).toEqual([
      expect.objectContaining({
        id: 'search-1',
        type: 'search',
        summary: '找到 2 张图片，1 段文本',
      }),
    ])
    expect(result.current.getEvidenceImages()).toEqual([
      expect.objectContaining({
        chunk_id: 'img-legacy',
        image_path: '/tmp/chart.png',
        page_no: 11,
        summary: 'Table VI',
      }),
    ])
  })
})
