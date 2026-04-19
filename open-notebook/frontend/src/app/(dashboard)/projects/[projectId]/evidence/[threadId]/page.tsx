import { ProjectEvidenceWorkspace } from '@/components/evidence/project-evidence-workspace'
import { evidenceThreadIdFromRoute } from '@/lib/project-evidence'
import { projectIdToNotebookId } from '@/lib/project-alias'

export default async function ProjectEvidenceThreadPage({
  params,
}: {
  params: Promise<{ projectId: string; threadId: string }>
}) {
  const { projectId, threadId } = await params

  return (
    <ProjectEvidenceWorkspace
      projectId={projectIdToNotebookId(projectId)}
      initialThreadId={evidenceThreadIdFromRoute(threadId)}
    />
  )
}
