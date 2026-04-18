import apiClient from './client'

import {
  CommandExecutionRequest,
  CommandJobCancelResponse,
  CommandJobListItemResponse,
  CommandJobResponse,
  CommandJobStatusResponse,
} from '@/lib/types/api'

export const commandsApi = {
  execute: async (data: CommandExecutionRequest) => {
    const response = await apiClient.post<CommandJobResponse>('/commands/jobs', data)
    return response.data
  },

  getJob: async (jobId: string) => {
    const response = await apiClient.get<CommandJobStatusResponse>(
      `/commands/jobs/${encodeURIComponent(jobId)}`
    )
    return response.data
  },

  listJobs: async (params?: {
    commandFilter?: string
    statusFilter?: string
    limit?: number
  }) => {
    const response = await apiClient.get<CommandJobListItemResponse[]>('/commands/jobs', {
      params: {
        command_filter: params?.commandFilter,
        status_filter: params?.statusFilter,
        limit: params?.limit,
      },
    })
    return response.data
  },

  retryJob: async (jobId: string) => {
    const response = await apiClient.post<CommandJobResponse>(
      `/commands/jobs/${encodeURIComponent(jobId)}/retry`
    )
    return response.data
  },

  cancelJob: async (jobId: string) => {
    const response = await apiClient.delete<CommandJobCancelResponse>(
      `/commands/jobs/${encodeURIComponent(jobId)}`
    )
    return response.data
  },
}
