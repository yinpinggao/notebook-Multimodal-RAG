import { redirect } from 'next/navigation'

import { buildProjectPath } from '@/lib/project-paths'

export default async function ProjectIndexPage({
  params,
}: {
  params: Promise<{ projectId: string }>
}) {
  const { projectId } = await params
  redirect(buildProjectPath({ projectId }))
}
