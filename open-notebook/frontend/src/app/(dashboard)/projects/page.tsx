'use client'

import Link from 'next/link'
import { useMemo } from 'react'
import { useRouter } from 'next/navigation'
import type { ComponentType } from 'react'
import {
  ArrowRight,
  Compass,
  FolderOpenDot,
  History,
  PlayCircle,
  Plus,
  Upload,
} from 'lucide-react'

import { EmptyState } from '@/components/common/EmptyState'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { AppShell } from '@/components/layout/AppShell'
import { ActionGrid, AutoGrid, PageContainer, PageHeader } from '@/components/projects/page-templates'
import { ProjectCard } from '@/components/projects/project-card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import { useProjectThreads } from '@/lib/hooks/use-project-evidence'
import { useCreateDemoProject, useProjects } from '@/lib/hooks/use-projects'
import { buildContinueProjectPath, buildProjectPath } from '@/lib/project-paths'
import { formatApiError } from '@/lib/utils/error-handler'
import {
  ProjectWorkspaceSummary,
  formatProjectTimestamp,
  projectSummaryToWorkspaceSummary,
} from '@/lib/project-workspace'
import { useAssistantWorkspaceStore } from '@/lib/stores/assistant-workspace-store'

function isDemoProject(project: ProjectWorkspaceSummary) {
  return /demo|智研舱/i.test(`${project.name} ${project.description}`)
}

function buildRecentActivity(projects: ProjectWorkspaceSummary[]) {
  return [...projects]
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
    .slice(0, 4)
    .map((project) => ({
      id: `activity:${project.id}`,
      title: project.name,
      detail:
        project.sourceCount > 0
          ? `最近整理了 ${project.sourceCount} 份资料。`
          : '项目刚建立，适合先导入规则、论文或演示材料。',
      updatedAt: project.updatedAt,
    }))
}

function ActionCard({
  title,
  description,
  href,
  onClick,
  icon: Icon,
}: {
  title: string
  description: string
  href?: string
  onClick?: () => void
  icon: ComponentType<{ className?: string }>
}) {
  const content = (
    <div className="flex h-full flex-col justify-between rounded-md border border-border/70 bg-background p-4 transition-colors hover:border-foreground/20 hover:bg-muted/20">
      <div className="space-y-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md border border-border/70 bg-muted/30">
          <Icon className="h-4 w-4" />
        </div>
        <div className="space-y-1">
          <div className="text-sm font-semibold">{title}</div>
          <div className="text-sm leading-6 text-muted-foreground">{description}</div>
        </div>
      </div>
      <div className="mt-4 flex items-center text-sm text-foreground">
        进入
        <ArrowRight className="ml-2 h-4 w-4" />
      </div>
    </div>
  )

  if (href) {
    return <Link href={href}>{content}</Link>
  }

  return (
    <button type="button" className="h-full text-left" onClick={onClick}>
      {content}
    </button>
  )
}

export default function ProjectsPage() {
  const router = useRouter()
  const { openNotebookDialog, openSourceDialog } = useCreateDialogs()
  const createDemoProject = useCreateDemoProject()
  const { lastProjectId, lastEvidenceThreadId } = useAssistantWorkspaceStore()
  const {
    data: projectSummaries = [],
    isLoading,
    error,
  } = useProjects(false)

  const projects = useMemo(
    () =>
      projectSummaries.map((project) => projectSummaryToWorkspaceSummary(project)),
    [projectSummaries]
  )

  const continueProject = useMemo(() => {
    if (lastProjectId) {
      const project = projects.find((item) => item.id === lastProjectId)
      if (project) {
        return project
      }
    }

    return [...projects].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))[0]
  }, [lastProjectId, projects])

  const { data: continueThreads = [] } = useProjectThreads(continueProject?.id || '')

  const continueHref = buildContinueProjectPath({
    projectId: continueProject?.id,
    lastProjectId,
    lastEvidenceThreadId,
    threads: continueThreads,
  })

  const demoProject = projects.find(isDemoProject)
  const recentActivity = buildRecentActivity(projects)

  const handleCreateOrOpenDemo = async () => {
    try {
      const project = await createDemoProject.mutateAsync()
      router.push(buildProjectPath({
        projectId: project.id,
        section: 'overview',
      }))
    } catch {
      // rendered inline
    }
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <PageContainer className="px-6 py-6">
          <PageHeader
            eyebrow={<Badge variant="outline">Project Workspace</Badge>}
            title="智研舱"
            description="先从项目进入。看清当前项目，再继续证据、对比、记忆和输出。"
            actions={
              <>
                <Button variant="outline" onClick={handleCreateOrOpenDemo} disabled={createDemoProject.isPending}>
                  {createDemoProject.isPending ? '准备 Demo...' : '打开 Demo'}
                </Button>
                <Button onClick={openNotebookDialog}>
                  <Plus className="mr-2 h-4 w-4" />
                  新建项目
                </Button>
              </>
            }
          />

          <section className="space-y-3">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold">从这里继续</h2>
              <p className="text-sm leading-6 text-muted-foreground">
                第一屏只保留几个明确动作，先进入项目，再继续具体工作流。
              </p>
            </div>

            <ActionGrid>
              <ActionCard
                title="新建项目"
                description="创建一个新的项目空间，把资料和输出收拢到一条主线上。"
                onClick={openNotebookDialog}
                icon={Plus}
              />
              <ActionCard
                title="继续最近项目"
                description={
                  continueProject
                    ? `继续 ${continueProject.name}`
                    : '打开最近整理的项目，直接回到上一次停下来的地方。'
                }
                href={continueHref}
                icon={PlayCircle}
              />
              <ActionCard
                title="导入资料"
                description="把论文、规则、PPT 或网页导入某个项目，再开始提问。"
                onClick={openSourceDialog}
                icon={Upload}
              />
              <ActionCard
                title="打开 Demo"
                description="进入预置演示路径，直接体验一条完整的项目工作流。"
                onClick={() => {
                  void handleCreateOrOpenDemo()
                }}
                icon={Compass}
              />
            </ActionGrid>
          </section>

          <section className="space-y-3">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold">最近项目</h2>
                <p className="text-sm leading-6 text-muted-foreground">
                  所有项目从这里进入，默认先到项目总览。
                </p>
              </div>
              <Badge variant="outline">{projects.length} 个项目</Badge>
            </div>

            {error ? (
              <Card className="border-destructive/40">
                <CardContent className="py-6 text-sm text-destructive">
                  项目列表暂时加载失败：{formatApiError(error)}
                </CardContent>
              </Card>
            ) : isLoading ? (
              <div className="flex min-h-48 items-center justify-center rounded-md border border-dashed border-border/70">
                <LoadingSpinner size="lg" />
              </div>
            ) : projects.length === 0 ? (
              <Card className="border-dashed border-border/70">
                <CardContent className="py-12">
                  <EmptyState
                    icon={FolderOpenDot}
                    title="还没有项目"
                    description="先创建一个项目空间，再把资料、证据和输出收进来。"
                    action={<Button onClick={openNotebookDialog}>创建第一个项目</Button>}
                  />
                </CardContent>
              </Card>
            ) : (
              <AutoGrid>
                {projects.map((project) => (
                  <ProjectCard
                    key={project.id}
                    project={project}
                    href={buildProjectPath({ projectId: project.id, section: 'overview' })}
                    ctaLabel="打开项目"
                  />
                ))}
              </AutoGrid>
            )}
          </section>

          <AutoGrid minItemWidth={360}>
            <Card className="border-border/70">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Compass className="h-4 w-4 text-muted-foreground" />
                  <CardTitle>Demo 路线</CardTitle>
                </div>
                <CardDescription>
                  先看一个项目首页，再进入证据、输出和运行轨迹。
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-md border border-border/70 p-4">
                  <div className="text-sm font-medium">3 分钟演示路径</div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {'项目总览 -> 证据问答 -> 输出工坊 -> 运行轨迹。'}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => void handleCreateOrOpenDemo()} disabled={createDemoProject.isPending}>
                    {createDemoProject.isPending ? '准备 Demo...' : '创建 / 打开 Demo'}
                  </Button>
                  {demoProject ? (
                    <Button asChild variant="outline">
                      <Link href={buildProjectPath({ projectId: demoProject.id, section: 'overview' })}>
                        打开现有 Demo
                      </Link>
                    </Button>
                  ) : null}
                </div>
                {createDemoProject.error ? (
                  <div className="text-sm text-destructive">
                    {formatApiError(createDemoProject.error)}
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card className="border-border/70">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <History className="h-4 w-4 text-muted-foreground" />
                  <CardTitle>最近活动</CardTitle>
                </div>
                <CardDescription>最近整理过的项目会优先出现在这里。</CardDescription>
              </CardHeader>
              <CardContent>
                {recentActivity.length === 0 ? (
                  <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                    创建项目后，最近活动会出现在这里。
                  </div>
                ) : (
                  <div className="space-y-3">
                    {recentActivity.map((activity) => (
                      <div key={activity.id} className="rounded-md border border-border/70 p-3">
                        <div className="text-sm font-medium">{activity.title}</div>
                        <div className="mt-1 text-sm text-muted-foreground">{activity.detail}</div>
                        <div className="mt-2 text-xs text-muted-foreground">
                          {formatProjectTimestamp(activity.updatedAt)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </AutoGrid>
        </PageContainer>
      </div>
    </AppShell>
  )
}
