'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { projectsApi } from '@/lib/api/projects'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { ProjectCompareRequest } from '@/lib/types/api'

const COMPARE_POLL_INTERVAL_MS = 2000

export function useCreateProjectCompare(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ProjectCompareRequest) => projectsApi.compare(projectId, data),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectCompares(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectCompare(projectId, response.compare_id),
      })
    },
  })
}

export function useProjectCompares(projectId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.projectCompares(projectId),
    queryFn: () => projectsApi.listCompares(projectId),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const compares = query.state.data || []
      return compares.some((compare) => compare.status === 'queued' || compare.status === 'running')
        ? COMPARE_POLL_INTERVAL_MS
        : false
    },
  })
}

export function useProjectCompare(projectId: string, compareId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.projectCompare(projectId, compareId || ''),
    queryFn: () => projectsApi.getCompare(projectId, compareId || ''),
    enabled: !!projectId && !!compareId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'queued' || status === 'running' ? COMPARE_POLL_INTERVAL_MS : false
    },
  })
}

export function useExportProjectCompare(projectId: string) {
  return useMutation({
    mutationFn: (compareId: string) => projectsApi.exportCompare(projectId, compareId),
  })
}
