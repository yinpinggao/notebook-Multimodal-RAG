'use client'

import Link from 'next/link'
import { useEffect } from 'react'
import { useParams, usePathname } from 'next/navigation'

import { AppShell } from '@/components/layout/AppShell'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { PageContainer, PageHeader } from '@/components/projects/page-templates'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useNotebook } from '@/lib/hooks/use-notebooks'
import { buildProjectPath, type ProjectSection } from '@/lib/project-paths'
import { projectIdToNotebookId } from '@/lib/project-alias'
import { useAssistantWorkspaceStore } from '@/lib/stores/assistant-workspace-store'
import { cn } from '@/lib/utils'

const PROJECT_TABS: Array<{ section: ProjectSection; labelKey: 'overview' | 'evidence' | 'compare' | 'memory' | 'outputs' | 'runs' }> = [
  { section: 'overview', labelKey: 'overview' },
  { section: 'evidence', labelKey: 'evidence' },
  { section: 'compare', labelKey: 'compare' },
  { section: 'memory', labelKey: 'memory' },
  { section: 'outputs', labelKey: 'outputs' },
  { section: 'runs', labelKey: 'runs' },
]

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { t } = useTranslation()
  const pathname = usePathname()
  const params = useParams()
  const routeProjectId = params?.projectId ? String(params.projectId) : ''
  const notebookId = projectIdToNotebookId(routeProjectId)
  const { data: notebook, isLoading } = useNotebook(notebookId)
  const { setLastProjectId } = useAssistantWorkspaceStore()

  useEffect(() => {
    if (routeProjectId) {
      setLastProjectId(routeProjectId)
    }
  }, [routeProjectId, setLastProjectId])

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <PageContainer className="px-6 py-6">
          <PageHeader
            eyebrow={
              <>
                <Badge variant="outline">Project Workspace</Badge>
                <Badge variant="secondary">证据优先</Badge>
              </>
            }
            title={notebook?.name || '项目空间'}
            description={
              notebook?.description ||
              '先看清项目现在的状态，再进入证据、对比、记忆、输出和运行。'
            }
            actions={
              <>
                <Button asChild variant="outline" size="sm">
                  <Link href={`/notebooks/${encodeURIComponent(notebookId)}`}>资料工作区</Link>
                </Button>
                <Button asChild variant="outline" size="sm">
                  <Link href={`/notebooks/${encodeURIComponent(notebookId)}/visual`}>视觉证据</Link>
                </Button>
              </>
            }
          />

          {isLoading ? (
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <LoadingSpinner size="sm" />
              正在载入项目信息...
            </div>
          ) : null}

          <nav className="flex flex-wrap gap-2 border-b border-border/70 pb-4">
            {PROJECT_TABS.map((tab) => {
              const href = buildProjectPath({
                projectId: notebookId || routeProjectId,
                section: tab.section,
              })
              const isActive = pathname === href || pathname.startsWith(`${href}/`)

              return (
                <Link
                  key={tab.section}
                  href={href}
                  className={cn(
                    'inline-flex items-center rounded-md border px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'border-foreground bg-foreground text-background'
                      : 'border-border bg-background text-muted-foreground hover:border-foreground/20 hover:text-foreground'
                  )}
                >
                  {t.navigation[tab.labelKey]}
                </Link>
              )
            })}
          </nav>

          <section className="space-y-6">{children}</section>
        </PageContainer>
      </div>
    </AppShell>
  )
}
