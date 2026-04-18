'use client'

import { useQuery } from '@tanstack/react-query'

import { projectsApi } from '@/lib/api/projects'
import { QUERY_KEYS } from '@/lib/api/query-client'

const RUN_POLL_INTERVAL_MS = 2000
const ACTIVE_STATUSES = new Set(['queued', 'running', 'waiting_review'])

export function useProjectRuns(projectId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.projectRuns(projectId),
    queryFn: () => projectsApi.listRuns(projectId),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const runs = query.state.data || []
      return runs.some((run) => ACTIVE_STATUSES.has(run.status))
        ? RUN_POLL_INTERVAL_MS
        : false
    },
  })
}

export function useProjectRun(projectId: string, runId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.projectRun(projectId, runId || ''),
    queryFn: () => projectsApi.getRun(projectId, runId || ''),
    enabled: !!projectId && !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && ACTIVE_STATUSES.has(status) ? RUN_POLL_INTERVAL_MS : false
    },
  })
}
