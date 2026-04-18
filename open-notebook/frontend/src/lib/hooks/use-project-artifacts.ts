'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { projectsApi } from '@/lib/api/projects'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { ProjectArtifactRequest } from '@/lib/types/api'

const ARTIFACT_POLL_INTERVAL_MS = 2000

export function useProjectArtifacts(projectId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.projectArtifacts(projectId),
    queryFn: () => projectsApi.listArtifacts(projectId),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const artifacts = query.state.data || []
      return artifacts.some((artifact) => artifact.status === 'queued' || artifact.status === 'running')
        ? ARTIFACT_POLL_INTERVAL_MS
        : false
    },
  })
}

export function useProjectArtifact(projectId: string, artifactId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.projectArtifact(projectId, artifactId || ''),
    queryFn: () => projectsApi.getArtifact(projectId, artifactId || ''),
    enabled: !!projectId && !!artifactId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'queued' || status === 'running' ? ARTIFACT_POLL_INTERVAL_MS : false
    },
  })
}

export function useCreateProjectArtifact(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ProjectArtifactRequest) => projectsApi.createArtifact(projectId, data),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectArtifacts(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectArtifact(projectId, response.artifact_id),
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
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectRun(projectId, response.created_by_run_id),
      })
    },
  })
}

export function useRegenerateProjectArtifact(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (artifactId: string) => projectsApi.regenerateArtifact(projectId, artifactId),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectArtifacts(projectId),
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectArtifact(projectId, response.artifact_id),
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
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectRun(projectId, response.created_by_run_id),
      })
    },
  })
}
