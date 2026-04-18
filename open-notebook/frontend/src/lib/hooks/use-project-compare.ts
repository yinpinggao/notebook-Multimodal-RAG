'use client'

import { useMutation, useQuery } from '@tanstack/react-query'

import { projectsApi } from '@/lib/api/projects'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { ProjectCompareRequest } from '@/lib/types/api'

const COMPARE_POLL_INTERVAL_MS = 2000

export function useCreateProjectCompare(projectId: string) {
  return useMutation({
    mutationFn: (data: ProjectCompareRequest) => projectsApi.compare(projectId, data),
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
