'use client'

import Link from 'next/link'
import { useParams, usePathname } from 'next/navigation'

import { AppShell } from '@/components/layout/AppShell'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'
import { cn } from '@/lib/utils'
import { useNotebook } from '@/lib/hooks/use-notebooks'
import { projectIdToNotebookId } from '@/lib/project-alias'

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { t } = useTranslation()
  const params = useParams()
  const pathname = usePathname()
  const routeProjectId = params?.projectId ? String(params.projectId) : ''
  const notebookId = projectIdToNotebookId(routeProjectId)
  const { data: notebook, isLoading } = useNotebook(notebookId)
  const projectTabs = [
    { name: t.navigation.overview, href: 'overview' },
    { name: t.navigation.evidence, href: 'evidence' },
    { name: t.navigation.compare, href: 'compare' },
    { name: t.navigation.memory, href: 'memory' },
    { name: t.navigation.outputs, href: 'outputs' },
    { name: t.navigation.runs, href: 'runs' },
  ] as const

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
          <header className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">Project Workspace</Badge>
              <Badge variant="secondary">证据优先</Badge>
            </div>

            {isLoading ? (
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <LoadingSpinner size="sm" />
                正在载入项目别名信息...
              </div>
            ) : (
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-1">
                  <h1 className="text-2xl font-semibold tracking-tight">
                    {notebook?.name || '项目空间'}
                  </h1>
                  <p className="text-sm text-muted-foreground">
                    {notebook?.description || '把资料、证据和输出收进同一个项目空间，围绕一个主线持续推进。'}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button asChild variant="outline" size="sm">
                    <Link href={`/notebooks/${encodeURIComponent(notebookId)}`}>资料工作区</Link>
                  </Button>
                  <Button asChild variant="outline" size="sm">
                    <Link href={`/notebooks/${encodeURIComponent(notebookId)}/visual`}>视觉证据</Link>
                  </Button>
                </div>
              </div>
            )}
          </header>

          <nav className="flex flex-wrap gap-2 border-b pb-4">
            {projectTabs.map((tab) => {
              const href = `/projects/${encodeURIComponent(notebookId || routeProjectId)}/${tab.href}`
              const isActive = pathname === href

              return (
                <Link
                  key={tab.href}
                  href={href}
                  className={cn(
                    'inline-flex items-center rounded-md border px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-border bg-background hover:border-primary/40 hover:text-foreground'
                  )}
                >
                  {tab.name}
                </Link>
              )
            })}
          </nav>

          <section className="space-y-6">{children}</section>
        </div>
      </div>
    </AppShell>
  )
}
