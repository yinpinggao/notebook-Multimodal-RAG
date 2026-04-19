import { ProjectEvidenceWorkspace } from '@/components/evidence/project-evidence-workspace'
import { projectIdToNotebookId } from '@/lib/project-alias'

export default async function ProjectEvidencePage({
  params,
}: {
  params: Promise<{ projectId: string }>
}) {
  const { projectId } = await params

  return <ProjectEvidenceWorkspace projectId={projectIdToNotebookId(projectId)} />
}
