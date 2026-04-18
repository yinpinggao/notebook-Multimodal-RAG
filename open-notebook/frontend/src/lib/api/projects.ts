import apiClient from './client'
import {
  AgentRunResponse,
  ArtifactRecordResponse,
  CreateProjectRequest,
  EvidenceThreadDetailResponse,
  EvidenceThreadSummaryResponse,
  MemoryRecordResponse,
  ProjectArtifactCreateResponse,
  ProjectArtifactRequest,
  ProjectCompareCreateResponse,
  ProjectCompareExportResponse,
  ProjectCompareRecordResponse,
  ProjectCompareRequest,
  ProjectAskRequest,
  ProjectAskResponse,
  ProjectMemoryDeleteResponse,
  ProjectMemoryRebuildResponse,
  ProjectMemoryUpdateRequest,
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

  listMemory: async (id: string) => {
    const response = await apiClient.get<MemoryRecordResponse[]>(`/projects/${id}/memory`)
    return response.data
  },

  listRuns: async (id: string) => {
    const response = await apiClient.get<AgentRunResponse[]>(`/projects/${id}/runs`)
    return response.data
  },

  getRun: async (id: string, runId: string) => {
    const response = await apiClient.get<AgentRunResponse>(
      `/projects/${id}/runs/${encodeURIComponent(runId)}`
    )
    return response.data
  },

  updateMemory: async (id: string, memoryId: string, data: ProjectMemoryUpdateRequest) => {
    const response = await apiClient.patch<MemoryRecordResponse>(
      `/projects/${id}/memory/${encodeURIComponent(memoryId)}`,
      data
    )
    return response.data
  },

  deleteMemory: async (id: string, memoryId: string) => {
    const response = await apiClient.delete<ProjectMemoryDeleteResponse>(
      `/projects/${id}/memory/${encodeURIComponent(memoryId)}`
    )
    return response.data
  },

  rebuildMemory: async (id: string) => {
    const response = await apiClient.post<ProjectMemoryRebuildResponse>(
      `/projects/${id}/memory/rebuild`
    )
    return response.data
  },

  compare: async (id: string, data: ProjectCompareRequest) => {
    const response = await apiClient.post<ProjectCompareCreateResponse>(`/projects/${id}/compare`, data)
    return response.data
  },

  getCompare: async (id: string, compareId: string) => {
    const response = await apiClient.get<ProjectCompareRecordResponse>(
      `/projects/${id}/compare/${encodeURIComponent(compareId)}`
    )
    return response.data
  },

  exportCompare: async (id: string, compareId: string) => {
    const response = await apiClient.post<ProjectCompareExportResponse>(
      `/projects/${id}/compare/${encodeURIComponent(compareId)}/export`
    )
    return response.data
  },

  listCompares: async (id: string) => {
    const response = await apiClient.get<ProjectCompareRecordResponse[]>(`/projects/${id}/compare`)
    return response.data
  },

  listArtifacts: async (id: string) => {
    const response = await apiClient.get<ArtifactRecordResponse[]>(`/projects/${id}/artifacts`)
    return response.data
  },

  getArtifact: async (id: string, artifactId: string) => {
    const response = await apiClient.get<ArtifactRecordResponse>(
      `/projects/${id}/artifacts/${encodeURIComponent(artifactId)}`
    )
    return response.data
  },

  createArtifact: async (id: string, data: ProjectArtifactRequest) => {
    const response = await apiClient.post<ProjectArtifactCreateResponse>(
      `/projects/${id}/artifacts`,
      data
    )
    return response.data
  },

  regenerateArtifact: async (id: string, artifactId: string) => {
    const response = await apiClient.post<ProjectArtifactCreateResponse>(
      `/projects/${id}/artifacts/${encodeURIComponent(artifactId)}/regenerate`
    )
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
