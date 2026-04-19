import { redirect } from 'next/navigation'

import { buildAssistantUrl } from '@/lib/assistant-workspace'

export default async function ProjectIndexPage({
  params,
}: {
  params: Promise<{ projectId: string }>
}) {
  const { projectId } = await params
  redirect(
    buildAssistantUrl({
      projectId: decodeURIComponent(projectId),
      view: 'knowledge',
    })
  )
}
