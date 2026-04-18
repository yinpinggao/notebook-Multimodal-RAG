import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { projectsApi } from '@/lib/api/projects'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useCreateDemoProject } from './use-projects'

vi.mock('@/lib/api/projects', () => ({
  projectsApi: {
    createDemo: vi.fn(),
  },
}))

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useCreateDemoProject', () => {
  it('invalidates project list and overview after creating demo project', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')

    vi.mocked(projectsApi.createDemo).mockResolvedValue({
      id: 'project:demo',
      name: '智研舱 Demo 项目',
      description: '用于演示的预置项目空间。',
      status: 'active',
      created_at: '2026-04-19T08:00:00Z',
      updated_at: '2026-04-19T08:05:00Z',
      source_count: 2,
      artifact_count: 1,
      memory_count: 2,
      last_run_at: '2026-04-19T08:05:00Z',
    })

    const { result } = renderHook(() => useCreateDemoProject(), {
      wrapper: createWrapper(queryClient),
    })

    await act(async () => {
      await result.current.mutateAsync()
    })

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projects,
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: QUERY_KEYS.projectOverview('project:demo'),
    })
  })
})
