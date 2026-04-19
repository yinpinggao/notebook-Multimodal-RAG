'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { AlertCircle, Compass, FolderOpenDot, History, Sparkles } from 'lucide-react'

import { EmptyState } from '@/components/common/EmptyState'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { AppShell } from '@/components/layout/AppShell'
import { ProjectCard } from '@/components/projects/project-card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import { useCreateDemoProject, useProjects } from '@/lib/hooks/use-projects'
import { buildAssistantUrl } from '@/lib/assistant-workspace'
import { formatApiError } from '@/lib/utils/error-handler'
import {
  ProjectWorkspaceSummary,
  formatProjectTimestamp,
  projectSummaryToWorkspaceSummary,
} from '@/lib/project-workspace'

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

function buildRecentOutputSuggestions(projects: ProjectWorkspaceSummary[]) {
  if (projects.length === 0) {
    return [
      '项目综述',
      '答辩提纲',
      '评委问题清单',
    ]
  }

  return [
    `${projects[0].name} · 项目综述`,
    `${projects[0].name} · 答辩提纲`,
    '问答卡片',
  ]
}

export default function ProjectsPage() {
  const router = useRouter()
  const { openNotebookDialog } = useCreateDialogs()
  const createDemoProject = useCreateDemoProject()
  const {
    data: projectSummaries = [],
    isLoading,
    error,
  } = useProjects(false)
  const projects = projectSummaries.map((project) =>
    projectSummaryToWorkspaceSummary(project)
  )
  const demoProject = projects.find(isDemoProject)
  const recentActivity = buildRecentActivity(projects)
  const outputSuggestions = buildRecentOutputSuggestions(projects)

  const handleCreateOrOpenDemo = async () => {
    try {
      const project = await createDemoProject.mutateAsync()
      router.push(buildAssistantUrl({ projectId: project.id, view: 'knowledge' }))
    } catch {}
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
          <header className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">项目空间 / Project Workspace</Badge>
                <Badge variant="secondary">证据优先</Badge>
              </div>

              <div className="space-y-2">
                <h1 className="text-3xl font-semibold tracking-tight">项目</h1>
                <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
                  从项目而不是工具入口开始整理资料。先看清每个项目的状态，再进入证据、对比、记忆和输出。
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => {
                  void handleCreateOrOpenDemo()
                }}
                disabled={createDemoProject.isPending}
              >
                {createDemoProject.isPending ? '正在准备 Demo...' : '创建 / 打开 Demo 项目'}
              </Button>
              <Button onClick={openNotebookDialog}>新建项目</Button>
              <Button asChild variant="outline">
                <Link href="/projects/new">打开新建页</Link>
              </Button>
            </div>
          </header>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_360px]">
            <section className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">项目列表</h2>
                  <p className="text-sm text-muted-foreground">
                    把资料、证据和产物统一收进项目空间，再围绕一个主线持续推进。
                  </p>
                </div>
                <Badge variant="outline">{projects.length} 个项目</Badge>
              </div>

              {error ? (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>项目列表暂时加载失败</AlertTitle>
                  <AlertDescription>{formatApiError(error)}</AlertDescription>
                </Alert>
              ) : isLoading ? (
                <div className="flex min-h-72 items-center justify-center rounded-lg border border-dashed border-border/70">
                  <LoadingSpinner size="lg" />
                </div>
              ) : projects.length === 0 ? (
                <Card className="border-dashed border-border/70">
                  <CardContent className="py-12">
                    <EmptyState
                      icon={FolderOpenDot}
                      title="还没有项目"
                      description="先创建一个项目空间，把规则、论文、PPT 或网页资料放进来。"
                      action={<Button onClick={openNotebookDialog}>创建第一个项目</Button>}
                    />
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {projects.map((project) => (
                    <ProjectCard
                      key={project.id}
                      project={project}
                      href={buildAssistantUrl({ projectId: project.id, view: 'knowledge' })}
                    />
                  ))}
                </div>
              )}
            </section>

            <aside className="space-y-4">
              <Card className="border-border/70">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Compass className="h-4 w-4 text-muted-foreground" />
                    <CardTitle>演示项目入口</CardTitle>
                  </div>
                  <CardDescription>
                    先从一个项目总览进入，再继续追问、整理证据和生成输出。
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-md border border-border/70 p-4">
                    <div className="text-sm font-medium">智研舱 Demo 路线</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      进入一个项目空间，先看主题、风险和时间线，再跳去证据工作台继续提问。
                    </p>
                  </div>
                  <div className="grid gap-2">
                    <Button
                      className="w-full"
                      onClick={() => {
                        void handleCreateOrOpenDemo()
                      }}
                      disabled={createDemoProject.isPending}
                    >
                      {createDemoProject.isPending ? '正在准备 Demo...' : '创建 / 打开 Demo 项目'}
                    </Button>
                    {demoProject ? (
                      <Button asChild variant="outline" className="w-full">
                        <Link href={buildAssistantUrl({ projectId: demoProject.id, view: 'knowledge' })}>
                          打开示例路线
                        </Link>
                      </Button>
                    ) : (
                      <div className="rounded-md border border-dashed border-border/70 p-3 text-sm text-muted-foreground">
                        Demo 项目创建后，这里会直接打开它的总览页。
                      </div>
                    )}
                    <div className="grid gap-2 sm:grid-cols-2">
                      <Button asChild variant="outline">
                        <Link href="/admin/evals">评测中心</Link>
                      </Button>
                      <Button asChild variant="outline">
                        <Link href="/admin/jobs">任务队列</Link>
                      </Button>
                    </div>
                  </div>

                  {createDemoProject.error ? (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertTitle>Demo 项目暂时不可用</AlertTitle>
                      <AlertDescription>
                        {formatApiError(createDemoProject.error)}
                      </AlertDescription>
                    </Alert>
                  ) : null}
                </CardContent>
              </Card>

              <Card className="border-border/70">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <History className="h-4 w-4 text-muted-foreground" />
                    <CardTitle>最近活动</CardTitle>
                  </div>
                  <CardDescription>
                    最近整理过的项目会优先出现在这里，方便继续推进手头任务。
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {recentActivity.length === 0 ? (
                    <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                      创建项目后，最近整理过的资料和活动会出现在这里。
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {recentActivity.map((activity) => (
                        <div
                          key={activity.id}
                          className="rounded-md border border-border/70 p-3"
                        >
                          <div className="break-words text-sm font-medium">{activity.title}</div>
                          <div className="mt-1 text-sm text-muted-foreground">
                            {activity.detail}
                          </div>
                          <div className="mt-2 text-xs text-muted-foreground">
                            {formatProjectTimestamp(activity.updatedAt)}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="border-border/70">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-muted-foreground" />
                    <CardTitle>最近产物</CardTitle>
                  </div>
                  <CardDescription>
                    常见输出目标先挂在这里，方便你快速进入综述、提纲和问答卡片。
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {outputSuggestions.map((item) => (
                      <div
                        key={item}
                        className="rounded-md border border-border/70 px-3 py-3 text-sm"
                      >
                        <span className="break-words">{item}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </aside>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
