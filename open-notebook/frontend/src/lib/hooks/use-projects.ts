import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { projectsApi } from '@/lib/api/projects'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { CreateProjectRequest } from '@/lib/types/api'

export function useProjects(archived?: boolean) {
  return useQuery({
    queryKey: [...QUERY_KEYS.projects, { archived }],
    queryFn: () => projectsApi.list({ archived, order_by: 'updated desc' }),
  })
}

export function useProjectOverview(projectId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.projectOverview(projectId),
    queryFn: () => projectsApi.getOverview(projectId),
    enabled: !!projectId,
  })
}

export function useCreateDemoProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => projectsApi.createDemo(),
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projects,
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectOverview(project.id),
      })
    },
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateProjectRequest) => projectsApi.create(data),
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projects,
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectOverview(project.id),
      })
    },
  })
}
