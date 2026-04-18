'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { commandsApi } from '@/lib/api/commands'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { CommandExecutionRequest } from '@/lib/types/api'

const JOB_POLL_INTERVAL_MS = 2000
const ACTIVE_JOB_STATUSES = new Set(['queued', 'running'])

export interface AdminJobFilters {
  commandFilter?: string
  statusFilter?: string
  limit?: number
}

export function useCommandJobs(filters?: AdminJobFilters) {
  const queryFilters = filters ? { ...filters } : undefined

  return useQuery({
    queryKey: QUERY_KEYS.commandJobs(queryFilters),
    queryFn: () => commandsApi.listJobs(filters),
    refetchInterval: (query) => {
      const jobs = query.state.data || []
      return jobs.some((job) => ACTIVE_JOB_STATUSES.has(job.status))
        ? JOB_POLL_INTERVAL_MS
        : false
    },
  })
}

export function useCommandJob(jobId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.commandJob(jobId || ''),
    queryFn: () => commandsApi.getJob(jobId || ''),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && ACTIVE_JOB_STATUSES.has(status) ? JOB_POLL_INTERVAL_MS : false
    },
  })
}

export function useExecuteCommand() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CommandExecutionRequest) => commandsApi.execute(data),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.commands,
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.commandJob(response.job_id),
      })
    },
  })
}

export function useRetryCommandJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId: string) => commandsApi.retryJob(jobId),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.commands,
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.commandJob(response.job_id),
      })
    },
  })
}

export function useCancelCommandJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId: string) => commandsApi.cancelJob(jobId),
    onSuccess: async (_, jobId) => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.commands,
      })
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.commandJob(jobId),
      })
    },
  })
}
