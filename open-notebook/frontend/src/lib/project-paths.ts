export type ProjectSection =
  | 'overview'
  | 'workspace'
  | 'evidence'
  | 'compare'
  | 'memory'
  | 'outputs'
  | 'runs'
  | 'showcase'

export type GlobalSection = 'projects' | 'library' | 'system'

interface ContinueThreadCandidate {
  id: string
  updated_at: string
}

interface BuildProjectPathParams {
  projectId: string
  section?: ProjectSection | null
  threadId?: string | null
}

function safeEncode(value: string) {
  return encodeURIComponent(value)
}

export function buildGlobalPath(section: GlobalSection): string {
  if (section === 'library') {
    return '/library'
  }

  if (section === 'system') {
    return '/system'
  }

  return '/projects'
}

export function buildProjectPath({
  projectId,
  section = 'overview',
  threadId,
}: BuildProjectPathParams): string {
  const basePath = `/projects/${safeEncode(projectId)}`

  if (!section) {
    return basePath
  }

  if (section === 'evidence' && threadId) {
    return `${basePath}/evidence/${safeEncode(threadId)}`
  }

  return `${basePath}/${section}`
}

interface BuildContinueProjectPathParams {
  projectId?: string | null
  lastProjectId?: string | null
  lastEvidenceThreadId?: string | null
  threads?: ContinueThreadCandidate[]
}

export function buildContinueProjectPath({
  projectId,
  lastProjectId,
  lastEvidenceThreadId,
  threads = [],
}: BuildContinueProjectPathParams): string {
  if (!projectId) {
    return '/projects'
  }

  const recentThreadId =
    [...threads].sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0]?.id ??
    null
  const pinnedThreadId =
    projectId === lastProjectId &&
    lastEvidenceThreadId &&
    threads.some((thread) => thread.id === lastEvidenceThreadId)
      ? lastEvidenceThreadId
      : null
  const threadId = pinnedThreadId ?? recentThreadId

  return buildProjectPath({
    projectId,
    section: threadId ? 'evidence' : 'overview',
    threadId,
  })
}

export function isProjectRoute(pathname: string | null | undefined) {
  return pathname === '/projects' || pathname?.startsWith('/projects/')
}
