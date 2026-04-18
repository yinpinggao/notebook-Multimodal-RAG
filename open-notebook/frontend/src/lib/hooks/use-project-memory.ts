'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { projectsApi } from '@/lib/api/projects'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { ProjectMemoryUpdateRequest } from '@/lib/types/api'

export function useProjectMemory(projectId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.projectMemory(projectId),
    queryFn: () => projectsApi.listMemory(projectId),
    enabled: !!projectId,
  })
}

export function useUpdateProjectMemory(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: { memoryId: string; data: ProjectMemoryUpdateRequest }) =>
      projectsApi.updateMemory(projectId, params.memoryId, params.data),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectMemory(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectOverview(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projects,
      })
    },
  })
}

export function useDeleteProjectMemory(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (memoryId: string) => projectsApi.deleteMemory(projectId, memoryId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectMemory(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectOverview(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projects,
      })
    },
  })
}

export function useRebuildProjectMemory(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => projectsApi.rebuildMemory(projectId),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectMemory(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectOverview(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projects,
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectRuns(projectId),
      })
      if (response.run_id) {
        await queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.projectRun(projectId, response.run_id),
        })
      }
    },
  })
}
