import { ProjectAskMode, ProjectSummaryResponse } from '@/lib/types/api'

export type HarnessAgentId = 'research' | 'retrieval' | 'visual' | 'synthesis'
export type AssistantView = 'workspace' | 'knowledge' | 'memory'
export type AssistantMobileTab = 'knowledge' | 'chat' | 'memory'
export type AssistantContextItemType = 'source' | 'note' | 'memory'
export type AssistantContextMode = 'full' | 'insights'
export type AssistantKnowledgeItemType = 'source' | 'note'

export interface AssistantContextItem {
  id: string
  type: AssistantContextItemType
  label: string
  contextMode?: AssistantContextMode
}

export interface AssistantKnowledgeSelection {
  id: string
  type: AssistantKnowledgeItemType
}

export interface AssistantWorkspaceState {
  currentProjectId?: string
  currentAgent: HarnessAgentId
  currentThreadId?: string
  currentView: AssistantView
  knowledgeCollapsed: boolean
  memoryCollapsed: boolean
  mobileTab: AssistantMobileTab
  selectedContextItems: AssistantContextItem[]
  lastProjectId?: string
}

export const DEFAULT_ASSISTANT_VIEW: AssistantView = 'workspace'
export const DEFAULT_ASSISTANT_AGENT: HarnessAgentId = 'research'
export const DEFAULT_ASSISTANT_TAB: AssistantMobileTab = 'chat'

export const HARNESS_AGENT_TO_ASK_MODE: Record<HarnessAgentId, ProjectAskMode> = {
  research: 'auto',
  retrieval: 'text',
  visual: 'visual',
  synthesis: 'mixed',
}

export function sanitizeAssistantView(value?: string | null): AssistantView {
  if (value === 'knowledge' || value === 'memory' || value === 'workspace') {
    return value
  }
  return DEFAULT_ASSISTANT_VIEW
}

export function sanitizeHarnessAgent(value?: string | null): HarnessAgentId {
  if (
    value === 'research' ||
    value === 'retrieval' ||
    value === 'visual' ||
    value === 'synthesis'
  ) {
    return value
  }
  return DEFAULT_ASSISTANT_AGENT
}

export function buildAssistantUrl(params?: {
  projectId?: string | null
  view?: AssistantView | null
  agent?: HarnessAgentId | null
  threadId?: string | null
}): string {
  const searchParams = new URLSearchParams()

  if (params?.projectId) {
    searchParams.set('project', params.projectId)
  }
  if (params?.view && params.view !== DEFAULT_ASSISTANT_VIEW) {
    searchParams.set('view', params.view)
  }
  if (params?.agent && params.agent !== DEFAULT_ASSISTANT_AGENT) {
    searchParams.set('agent', params.agent)
  }
  if (params?.threadId) {
    searchParams.set('thread', params.threadId)
  }

  const query = searchParams.toString()
  return query ? `/assistant?${query}` : '/assistant'
}

export function mergeAssistantSearchParams(
  current: URLSearchParams | { toString(): string } | string | undefined,
  updates: {
    projectId?: string | null
    view?: AssistantView | null
    agent?: HarnessAgentId | null
    threadId?: string | null
  }
): string {
  const searchParams = new URLSearchParams(
    typeof current === 'string' ? current : current?.toString() || ''
  )

  const mappings: Array<[keyof typeof updates, string]> = [
    ['projectId', 'project'],
    ['view', 'view'],
    ['agent', 'agent'],
    ['threadId', 'thread'],
  ]

  mappings.forEach(([sourceKey, targetKey]) => {
    const value = updates[sourceKey]
    if (value === undefined) {
      return
    }
    if (value === null || value === '') {
      searchParams.delete(targetKey)
      return
    }
    searchParams.set(targetKey, value)
  })

  const query = searchParams.toString()
  return query ? `/assistant?${query}` : '/assistant'
}

export function groupAssistantContextItems(items: AssistantContextItem[]) {
  const sourceIds: string[] = []
  const noteIds: string[] = []
  const memoryIds: string[] = []

  items.forEach((item) => {
    if (item.type === 'source') {
      sourceIds.push(item.id)
    } else if (item.type === 'note') {
      noteIds.push(item.id)
    } else if (item.type === 'memory') {
      memoryIds.push(item.id)
    }
  })

  return { sourceIds, noteIds, memoryIds }
}

export function hasExplicitAssistantContext(items: AssistantContextItem[]) {
  return items.length > 0
}

export function resolveAssistantProjectId(params: {
  projects: ProjectSummaryResponse[]
  requestedProjectId?: string | null
  lastProjectId?: string | null
}): string | undefined {
  const projectIds = new Set(params.projects.map((project) => project.id))

  if (params.requestedProjectId && projectIds.has(params.requestedProjectId)) {
    return params.requestedProjectId
  }

  if (params.lastProjectId && projectIds.has(params.lastProjectId)) {
    return params.lastProjectId
  }

  return [...params.projects]
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0]?.id
}
