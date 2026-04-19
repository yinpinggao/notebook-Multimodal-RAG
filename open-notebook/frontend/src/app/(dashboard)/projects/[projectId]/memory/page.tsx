import { ProjectMemoryWorkspace } from '@/components/memory/project-memory-workspace'
import { projectIdToNotebookId } from '@/lib/project-alias'

export default async function ProjectMemoryPage({
  params,
}: {
  params: Promise<{ projectId: string }>
}) {
  const { projectId } = await params

  return <ProjectMemoryWorkspace projectId={projectIdToNotebookId(projectId)} />
}
