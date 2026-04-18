'use client'

import { useParams } from 'next/navigation'

import { ProjectEvidenceWorkspace } from '@/components/evidence/project-evidence-workspace'
import { evidenceThreadIdFromRoute } from '@/lib/project-evidence'
import { projectIdToNotebookId } from '@/lib/project-alias'

export default function ProjectEvidenceThreadPage() {
  const params = useParams()
  const routeProjectId = params?.projectId ? String(params.projectId) : ''
  const routeThreadId = params?.threadId ? String(params.threadId) : ''
  const projectId = projectIdToNotebookId(routeProjectId)
  const threadId = evidenceThreadIdFromRoute(routeThreadId)

  return (
    <ProjectEvidenceWorkspace
      projectId={projectId}
      initialThreadId={threadId}
    />
  )
}
