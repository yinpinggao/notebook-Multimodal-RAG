import { buildProjectPath } from '@/lib/project-paths'
import { ProjectAskMode } from '@/lib/types/api'

export interface EvidenceTarget {
  kind: 'source' | 'note' | 'insight'
  id: string
}

function safeDecodeRouteParam(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function stripInternalRefAnchor(value: string): string {
  return value.split('#')[0] || value
}

export const PROJECT_ASK_MODE_OPTIONS: Array<{
  value: ProjectAskMode
  label: string
  description: string
}> = [
  {
    value: 'auto',
    label: '自动',
    description: '优先让系统判断文本、视觉或联合问答。',
  },
  {
    value: 'text',
    label: '文本',
    description: '更偏向正文与笔记证据。',
  },
  {
    value: 'visual',
    label: '视觉',
    description: '更偏向图表、版面和截图相关问题。',
  },
  {
    value: 'mixed',
    label: '联合',
    description: '把文本与视觉证据一起组织。',
  },
]

export function evidenceThreadIdFromRoute(threadId: string): string {
  return safeDecodeRouteParam(threadId)
}

export function buildProjectEvidencePath(projectId: string, threadId?: string): string {
  return buildProjectPath({
    projectId,
    section: 'evidence',
    threadId,
  })
}

export function resolveEvidenceTarget(params: {
  sourceId?: string | null
  internalRef?: string | null
}): EvidenceTarget | null {
  const normalizedSourceId = (params.sourceId || '').trim()
  const normalizedInternalRef = stripInternalRefAnchor((params.internalRef || '').trim())
  const candidate = normalizedInternalRef || normalizedSourceId

  if (!candidate) {
    return null
  }

  if (candidate.startsWith('note:')) {
    return { kind: 'note', id: candidate }
  }

  if (candidate.startsWith('insight:') || candidate.startsWith('source_insight:')) {
    return { kind: 'insight', id: candidate }
  }

  return {
    kind: 'source',
    id: stripInternalRefAnchor(normalizedSourceId || candidate),
  }
}

export function canContinueEvidenceThread(params: {
  threadId?: string
  threadLoaded: boolean
  threadError: boolean
}): boolean {
  return Boolean(params.threadId && params.threadLoaded && !params.threadError)
}

export function formatEvidenceConfidence(confidence?: number | null): string {
  if (typeof confidence !== 'number' || Number.isNaN(confidence)) {
    return '待评估'
  }

  const normalized = Math.max(0, Math.min(1, confidence))
  return `${Math.round(normalized * 100)}%`
}
