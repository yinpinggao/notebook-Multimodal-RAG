import { useQuery } from '@tanstack/react-query'

import { projectsApi } from '@/lib/api/projects'
import { QUERY_KEYS } from '@/lib/api/query-client'

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
