'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'

import { QUERY_KEYS } from '@/lib/api/query-client'
import {
  CommandJobListItemResponse,
  CommandJobStatusResponse,
  ProjectEvalCommandInput,
  ProjectEvalOutputResponse,
} from '@/lib/types/api'
import { useCommandJob, useCommandJobs, useExecuteCommand } from './use-admin-jobs'

export const PROJECT_EVAL_COMMAND = 'run_project_eval'

export function useProjectEvalJobs(limit = 12) {
  return useCommandJobs({
    commandFilter: PROJECT_EVAL_COMMAND,
    limit,
  })
}

export function useProjectEvalJob(jobId?: string) {
  return useCommandJob(jobId)
}

export function useRunProjectEval() {
  const queryClient = useQueryClient()
  const executeCommand = useExecuteCommand()

  return useMutation({
    mutationFn: (input: ProjectEvalCommandInput) =>
      executeCommand.mutateAsync({
        app: 'open_notebook',
        command: PROJECT_EVAL_COMMAND,
        input: { ...input } as Record<string, unknown>,
      }),
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

function isEvalMetricArray(value: unknown): boolean {
  return Array.isArray(value)
}

export function readProjectEvalOutput(
  status?: Pick<CommandJobStatusResponse, 'result'> | null
): ProjectEvalOutputResponse | null {
  const result = status?.result
  if (!result || typeof result !== 'object') {
    return null
  }

  const candidate = result as Partial<ProjectEvalOutputResponse>
  if (
    typeof candidate.project_id !== 'string' ||
    typeof candidate.summary !== 'string' ||
    !isEvalMetricArray(candidate.metrics)
  ) {
    return null
  }

  return candidate as ProjectEvalOutputResponse
}

export function readProjectIdFromEvalJob(
  job?:
    | Pick<CommandJobListItemResponse, 'args' | 'result'>
    | Pick<CommandJobStatusResponse, 'result'>
    | null
) {
  const resultProjectId = readProjectEvalOutput(job)?.project_id
  if (resultProjectId) {
    return resultProjectId
  }

  if (job && 'args' in job && job.args && typeof job.args.project_id === 'string') {
    return job.args.project_id
  }

  return null
}
