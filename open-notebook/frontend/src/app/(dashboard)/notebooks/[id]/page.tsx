import { redirect } from 'next/navigation'

import { buildAssistantUrl } from '@/lib/assistant-workspace'

export default async function NotebookPageRedirect({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  redirect(buildAssistantUrl({ projectId: decodeURIComponent(id), view: 'knowledge' }))
}
