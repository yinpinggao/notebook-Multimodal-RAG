import { redirect } from 'next/navigation'

import { buildAssistantUrl } from '@/lib/assistant-workspace'
import { projectIdToNotebookId } from '@/lib/project-alias'

export default async function ProjectMemoryPageRedirect({
  params,
}: {
  params: Promise<{ projectId: string }>
}) {
  const { projectId } = await params
  redirect(
    buildAssistantUrl({
      projectId: projectIdToNotebookId(projectId),
      view: 'memory',
    })
  )
}
