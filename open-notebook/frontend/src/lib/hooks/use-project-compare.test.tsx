import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { projectsApi } from '@/lib/api/projects'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useCreateProjectCompare } from './use-project-compare'

vi.mock('@/lib/api/projects', () => ({
  projectsApi: {
    compare: vi.fn(),
  },
}))

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useCreateProjectCompare', () => {
  it('invalidates compare, overview, project list, and run queries after submit', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')

    vi.mocked(projectsApi.compare).mockResolvedValue({
      compare_id: 'compare:1',
      status: 'queued',
      command_id: 'command:1',
      run_id: 'run:compare001',
    })

    const { result } = renderHook(() => useCreateProjectCompare('project:demo'), {
      wrapper: createWrapper(queryClient),
    })

    await act(async () => {
      await result.current.mutateAsync({
        source_a_id: 'source:a',
        source_b_id: 'source:b',
      })
    })

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectCompares('project:demo'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectCompare('project:demo', 'compare:1'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectOverview('project:demo'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projects,
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectRuns('project:demo'),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectRun('project:demo', 'run:compare001'),
    })
  })
})
