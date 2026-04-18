import apiClient from './client'
import {
  CreateProjectRequest,
  EvidenceThreadDetailResponse,
  EvidenceThreadSummaryResponse,
  ProjectAskRequest,
  ProjectAskResponse,
  ProjectFollowupRequest,
  ProjectDeleteResponse,
  ProjectOverviewRebuildResponse,
  ProjectOverviewResponse,
  ProjectSummaryResponse,
} from '@/lib/types/api'

export const projectsApi = {
  list: async (params?: { archived?: boolean; order_by?: string }) => {
    const response = await apiClient.get<ProjectSummaryResponse[]>('/projects', { params })
    return response.data
  },

  create: async (data: CreateProjectRequest) => {
    const response = await apiClient.post<ProjectSummaryResponse>('/projects', data)
    return response.data
  },

  delete: async (id: string) => {
    const response = await apiClient.delete<ProjectDeleteResponse>(`/projects/${id}`)
    return response.data
  },

  getOverview: async (id: string) => {
    const response = await apiClient.get<ProjectOverviewResponse>(`/projects/${id}/overview`)
    return response.data
  },

  rebuildOverview: async (id: string) => {
    const response = await apiClient.post<ProjectOverviewRebuildResponse>(
      `/projects/${id}/overview/rebuild`
    )
    return response.data
  },

  ask: async (id: string, data: ProjectAskRequest) => {
    const response = await apiClient.post<ProjectAskResponse>(`/projects/${id}/ask`, data)
    return response.data
  },

  listThreads: async (id: string) => {
    const response = await apiClient.get<EvidenceThreadSummaryResponse[]>(`/projects/${id}/threads`)
    return response.data
  },

  getThread: async (id: string, threadId: string) => {
    const response = await apiClient.get<EvidenceThreadDetailResponse>(
      `/projects/${id}/threads/${encodeURIComponent(threadId)}`
    )
    return response.data
  },

  followup: async (id: string, threadId: string, data: ProjectFollowupRequest) => {
    const response = await apiClient.post<ProjectAskResponse>(
      `/projects/${id}/threads/${encodeURIComponent(threadId)}/followup`,
      data
    )
    return response.data
  },
}
