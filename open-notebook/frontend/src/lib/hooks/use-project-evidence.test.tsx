import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { projectsApi } from '@/lib/api/projects'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useAskProject, useFollowupProjectThread } from './use-project-evidence'

vi.mock('@/lib/api/projects', () => ({
  projectsApi: {
    ask: vi.fn(),
    followup: vi.fn(),
  },
}))

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useProjectEvidence mutations', () => {
  it('invalidates overview, project list, thread list, thread detail, and run queries after ask', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')

    vi.mocked(projectsApi.ask).mockResolvedValue({
      thread_id: 'thread:1',
      answer: 'done',
      confidence: 0.9,
      evidence_cards: [],
      memory_updates: [],
      run_id: 'run:ask001',
      suggested_followups: [],
      mode: 'mixed',
    })

    const { result } = renderHook(() => useAskProject('project:demo'), {
      wrapper: createWrapper(queryClient),
    })

    await act(async () => {
      await result.current.mutateAsync({ question: 'What changed?' })
    })

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectThreads('project:demo'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectOverview('project:demo'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projects,
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectThread('project:demo', 'thread:1'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectRuns('project:demo'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectRun('project:demo', 'run:ask001'),
    })
  })

  it('invalidates overview, project list, thread list, thread detail, and run queries after followup', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')

    vi.mocked(projectsApi.followup).mockResolvedValue({
      thread_id: 'thread:1',
      answer: 'done',
      confidence: 0.9,
      evidence_cards: [],
      memory_updates: [],
      run_id: 'run:ask002',
      suggested_followups: [],
      mode: 'mixed',
    })

    const { result } = renderHook(
      () => useFollowupProjectThread('project:demo', 'thread:1'),
      {
        wrapper: createWrapper(queryClient),
      }
    )

    await act(async () => {
      await result.current.mutateAsync({ question: 'Then what?' })
    })

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectThreads('project:demo'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectOverview('project:demo'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projects,
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectThread('project:demo', 'thread:1'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectRuns('project:demo'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectRun('project:demo', 'run:ask002'),
    })
  })
})
