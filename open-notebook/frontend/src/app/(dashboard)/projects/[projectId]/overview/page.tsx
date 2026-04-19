'use client'

import Link from 'next/link'
import { useMemo } from 'react'
import type { ComponentType } from 'react'
import { useParams } from 'next/navigation'
import {
  Activity,
  AlertCircle,
  Boxes,
  BrainCircuit,
  FileOutput,
  Files,
  GitCompareArrows,
  MessageSquareQuote,
  Workflow,
} from 'lucide-react'

import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { ActionGrid, AutoGrid } from '@/components/projects/page-templates'
import { ProjectOverviewHeader } from '@/components/projects/project-overview-header'
import { RiskListCard } from '@/components/projects/risk-list-card'
import { TimelineCard } from '@/components/projects/timeline-card'
import { TopicClusterCard } from '@/components/projects/topic-cluster-card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useProjectOverview } from '@/lib/hooks/use-projects'
import { useNotebook } from '@/lib/hooks/use-notebooks'
import { useNotebookSources } from '@/lib/hooks/use-sources'
import { buildProjectPath } from '@/lib/project-paths'
import {
  buildProjectOverviewFromResponse,
  formatProjectTimestamp,
} from '@/lib/project-workspace'
import { projectIdToNotebookId } from '@/lib/project-alias'
import { formatApiError } from '@/lib/utils/error-handler'

function OverviewActionCard({
  title,
  description,
  href,
  icon: Icon,
}: {
  title: string
  description: string
  href: string
  icon: ComponentType<{ className?: string }>
}) {
  return (
    <Link href={href}>
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
      </div>
    </Link>
  )
}

export default function ProjectOverviewPage() {
  const params = useParams()
  const routeProjectId = params?.projectId ? String(params.projectId) : ''
  const projectId = projectIdToNotebookId(routeProjectId)
  const notebookId = projectId
  const {
    data: overviewResponse,
    isLoading: overviewLoading,
    error: overviewError,
  } = useProjectOverview(projectId)
  const { data: notebook } = useNotebook(notebookId)
  const {
    sources,
    isLoading: sourcesLoading,
    error: sourcesError,
  } = useNotebookSources(notebookId)

  const overview = useMemo(() => {
    if (!overviewResponse) {
      return null
    }

    return buildProjectOverviewFromResponse({
      overview: overviewResponse,
      sources,
      noteCount: notebook?.note_count,
    })
  }, [notebook?.note_count, overviewResponse, sources])

  if (overviewError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>项目总览暂时加载失败</AlertTitle>
        <AlertDescription className="space-y-3">
          <p>{formatApiError(overviewError)}</p>
          <Button asChild variant="outline" size="sm">
            <Link href="/projects">返回项目列表</Link>
          </Button>
        </AlertDescription>
      </Alert>
    )
  }

  if (overviewLoading || !overview) {
    return (
      <div className="flex min-h-[24rem] items-center justify-center rounded-lg border border-dashed border-border/70">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  const actionItems = [
    {
      title: '证据问答',
      description: '继续提问、追问，回到有 run_id 的证据链里。',
      href: buildProjectPath({ projectId: overview.project.id, section: 'evidence' }),
      icon: MessageSquareQuote,
    },
    {
      title: '文档对比',
      description: '把两份资料的差异、冲突和缺失点摊开看。',
      href: buildProjectPath({ projectId: overview.project.id, section: 'compare' }),
      icon: GitCompareArrows,
    },
    {
      title: '记忆中心',
      description: '审核长期记忆，决定哪些内容要留下来。',
      href: buildProjectPath({ projectId: overview.project.id, section: 'memory' }),
      icon: BrainCircuit,
    },
    {
      title: '输出工坊',
      description: '把项目综述、答辩提纲和问答卡片沉淀成成品。',
      href: buildProjectPath({ projectId: overview.project.id, section: 'outputs' }),
      icon: FileOutput,
    },
    {
      title: '运行轨迹',
      description: '回看 ask、compare、artifact 和记忆重建留下的步骤。',
      href: buildProjectPath({ projectId: overview.project.id, section: 'runs' }),
      icon: Workflow,
    },
  ]

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">下一步动作</h2>
          <p className="text-sm leading-6 text-muted-foreground">
            先选一个明确动作进入，避免把所有信息同时摊满一屏。
          </p>
        </div>
        <ActionGrid>
          {actionItems.map((item) => (
            <OverviewActionCard key={item.title} {...item} />
          ))}
        </ActionGrid>
      </section>

      <ProjectOverviewHeader project={overview.project} stats={overview.stats} />

      <AutoGrid minItemWidth={380}>
        <TopicClusterCard topics={overview.topics} keywords={overview.keywords} />
        <RiskListCard items={overview.risks} />
      </AutoGrid>

      <AutoGrid minItemWidth={380}>
        <TimelineCard events={overview.timelineEvents} />

        <Card className="border-border/70">
          <CardHeader>
            <div className="flex items-center gap-2">
              <MessageSquareQuote className="h-4 w-4 text-muted-foreground" />
              <CardTitle>推荐问题</CardTitle>
            </div>
            <CardDescription>
              先沿这些问题把项目主线跑通，再逐步补齐证据和输出。
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="space-y-3">
              {overview.recommendedQuestions.map((question, index) => (
                <div
                  key={`${question}-${index}`}
                  className="rounded-md border border-border/70 p-3"
                >
                  <div className="break-words text-sm leading-6">{question}</div>
                </div>
              ))}

              <Button asChild className="w-full">
                <Link href={buildProjectPath({ projectId: overview.project.id, section: 'evidence' })}>
                  进入证据工作台
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </AutoGrid>

      <AutoGrid minItemWidth={380}>
        <Card className="border-border/70">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <CardTitle>最近运行</CardTitle>
            </div>
            <CardDescription>
              重要任务会在这里沉淀为可回放的项目轨迹。
            </CardDescription>
          </CardHeader>

          <CardContent>
            {overview.recentRuns.length === 0 ? (
              <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                开始提问、整理资料或生成输出后，这里会留下本项目的任务轨迹。
              </div>
            ) : (
              <div className="space-y-3">
                {overview.recentRuns.map((run) => (
                  <div
                    key={run.id}
                    className="flex items-center justify-between rounded-md border border-border/70 p-3"
                  >
                    <div className="space-y-1">
                      <div className="text-sm font-medium">{run.runType}</div>
                      <div className="text-xs text-muted-foreground">
                        {formatProjectTimestamp(run.createdAt)}
                      </div>
                    </div>
                    <Badge variant="outline">{run.status}</Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/70">
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileOutput className="h-4 w-4 text-muted-foreground" />
              <CardTitle>最近产物</CardTitle>
            </div>
            <CardDescription>
              综述、差异报告和答辩提纲都会沉淀在这里。
            </CardDescription>
          </CardHeader>

          <CardContent>
            {overview.recentArtifacts.length === 0 ? (
              <div className="space-y-3">
                <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                  当前还没有项目产物。适合先从综述、问答卡片或答辩提纲开始。
                </div>
                <Button asChild variant="outline" className="w-full">
                  <Link href={buildProjectPath({ projectId: overview.project.id, section: 'outputs' })}>
                    打开输出工坊
                  </Link>
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {overview.recentArtifacts.map((artifact) => (
                  <div
                    key={artifact.id}
                    className="rounded-md border border-border/70 p-3"
                  >
                    <div className="text-sm font-medium">{artifact.title}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {artifact.artifactType} · {formatProjectTimestamp(artifact.createdAt)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </AutoGrid>

      <Card className="border-border/70">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Boxes className="h-4 w-4 text-muted-foreground" />
            <CardTitle>当前资料快照</CardTitle>
          </div>
          <CardDescription>
            先把项目里已经存在的资料状况盘清楚，再继续建立项目画像。
          </CardDescription>
        </CardHeader>

        <CardContent>
          {sourcesLoading && overview.sourceCount > 0 ? (
            <div className="flex min-h-40 items-center justify-center rounded-md border border-dashed border-border/70">
              <LoadingSpinner size="sm" />
            </div>
          ) : sourcesError && overview.sourceCount > 0 ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>资料快照暂时加载失败</AlertTitle>
              <AlertDescription>{formatApiError(sourcesError)}</AlertDescription>
            </Alert>
          ) : sources.length === 0 ? (
            <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
              还没有资料进入这个项目空间。先导入论文、规则文档、PPT 或截图，再回来生成项目画像。
            </div>
          ) : (
            <AutoGrid minItemWidth={280}>
              {sources.slice(0, 6).map((source) => (
                <div key={source.id} className="rounded-md border border-border/70 p-4">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Files className="h-3.5 w-3.5" />
                    <span>{source.title || '未命名资料'}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge variant="outline">
                      {source.embedded ? '文本索引已就绪' : '文本索引待完成'}
                    </Badge>
                    <Badge variant="outline">
                      {source.visual_index_status === 'completed'
                        ? '视觉索引已就绪'
                        : '视觉索引待完成'}
                    </Badge>
                  </div>
                  <div className="mt-3 text-xs text-muted-foreground">
                    最近更新 {formatProjectTimestamp(source.updated)}
                  </div>
                </div>
              ))}
            </AutoGrid>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
