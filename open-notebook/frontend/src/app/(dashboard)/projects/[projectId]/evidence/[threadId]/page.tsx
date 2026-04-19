import { redirect } from 'next/navigation'

import { buildAssistantUrl } from '@/lib/assistant-workspace'
import { evidenceThreadIdFromRoute } from '@/lib/project-evidence'
import { projectIdToNotebookId } from '@/lib/project-alias'

export default async function ProjectEvidenceThreadPageRedirect({
  params,
}: {
  params: Promise<{ projectId: string; threadId: string }>
}) {
  const { projectId, threadId } = await params
  redirect(
    buildAssistantUrl({
      projectId: projectIdToNotebookId(projectId),
      view: 'workspace',
      threadId: evidenceThreadIdFromRoute(threadId),
    })
  )
}
