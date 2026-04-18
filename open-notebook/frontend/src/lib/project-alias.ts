import { NotebookResponse } from '@/lib/types/api'

export interface ProjectAliasSummary {
  id: string
  notebookId: string
  name: string
  description: string
  archived: boolean
  created: string
  updated: string
  sourceCount: number
  noteCount: number
}

function safeDecodeRouteParam(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

export function projectIdToNotebookId(projectId: string): string {
  return safeDecodeRouteParam(projectId)
}

export function notebookIdToProjectId(notebookId: string): string {
  return notebookId
}

export function notebookToProjectSummary(
  notebook: NotebookResponse
): ProjectAliasSummary {
  return {
    id: notebookIdToProjectId(notebook.id),
    notebookId: notebook.id,
    name: notebook.name,
    description: notebook.description,
    archived: notebook.archived,
    created: notebook.created,
    updated: notebook.updated,
    sourceCount: notebook.source_count,
    noteCount: notebook.note_count,
  }
}
