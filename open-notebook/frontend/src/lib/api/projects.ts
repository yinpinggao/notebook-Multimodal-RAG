import apiClient from './client'
import {
  CreateProjectRequest,
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
}
