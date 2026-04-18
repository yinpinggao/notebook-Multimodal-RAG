'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { projectsApi } from '@/lib/api/projects'
import { QUERY_KEYS } from '@/lib/api/query-client'
import {
  ProjectAskRequest,
  ProjectFollowupRequest,
} from '@/lib/types/api'

export function useProjectThreads(projectId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.projectThreads(projectId),
    queryFn: () => projectsApi.listThreads(projectId),
    enabled: !!projectId,
  })
}

export function useProjectThread(projectId: string, threadId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.projectThread(projectId, threadId || ''),
    queryFn: () => projectsApi.getThread(projectId, threadId || ''),
    enabled: !!projectId && !!threadId,
  })
}

export function useAskProject(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ProjectAskRequest) => projectsApi.ask(projectId, data),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectThreads(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectOverview(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projects,
      })

      if (response.thread_id) {
        await queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.projectThread(projectId, response.thread_id),
        })
      }
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

export function useFollowupProjectThread(projectId: string, threadId?: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ProjectFollowupRequest) =>
      projectsApi.followup(projectId, threadId || '', data),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectThreads(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectOverview(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projects,
      })

      if (response.thread_id) {
        await queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.projectThread(projectId, response.thread_id),
        })
      }
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
