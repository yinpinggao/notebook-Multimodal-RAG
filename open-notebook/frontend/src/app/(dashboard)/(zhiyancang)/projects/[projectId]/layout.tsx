import type { ReactNode } from 'react'

import { ProjectSubnav } from '@/components/zhiyancang/layout/project-subnav'

export default async function ProjectLayout({
  children,
  params,
}: {
  children: ReactNode
  params: Promise<{ projectId: string }>
}) {
  const { projectId } = await params

  return (
    <div className="space-y-6">
      <ProjectSubnav projectId={projectId} />
      {children}
    </div>
  )
}
