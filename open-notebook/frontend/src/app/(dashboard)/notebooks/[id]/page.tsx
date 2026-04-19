import { redirect } from 'next/navigation'

import { buildProjectPath } from '@/lib/project-paths'

export default async function NotebookPageRedirect({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  redirect(buildProjectPath({ projectId: id }))
}
