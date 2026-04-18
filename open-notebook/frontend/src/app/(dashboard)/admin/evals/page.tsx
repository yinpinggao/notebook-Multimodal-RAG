'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { AlertCircle, CheckCircle2, ClipboardList, Loader2, ShieldAlert } from 'lucide-react'

import { EmptyState } from '@/components/common/EmptyState'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { AppShell } from '@/components/layout/AppShell'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  readProjectEvalOutput,
  readProjectIdFromEvalJob,
  useProjectEvalJob,
  useProjectEvalJobs,
  useRunProjectEval,
} from '@/lib/hooks/use-admin-evals'
import { useProjectCompares } from '@/lib/hooks/use-project-compare'
import { useProjectThreads } from '@/lib/hooks/use-project-evidence'
import { useProjects } from '@/lib/hooks/use-projects'
import { formatProjectTimestamp } from '@/lib/project-workspace'
import { EvalMetricResultResponse } from '@/lib/types/api'
import { formatApiError } from '@/lib/utils/error-handler'

const AUTO_VALUE = '__auto__'

function normalizeMetricStatus(status: string) {
  if (status === 'pass' || status === 'passed') {
    return 'passed'
  }
  if (status === 'fail' || status === 'failed') {
    return 'failed'
  }
  return 'unavailable'
}

function metricBadgeVariant(status: string) {
  if (normalizeMetricStatus(status) === 'passed') {
    return 'default'
  }
  if (normalizeMetricStatus(status) === 'failed') {
    return 'destructive'
  }
  return 'outline'
}

function metricLabel(status: string) {
  if (normalizeMetricStatus(status) === 'passed') {
    return '通过'
  }
  if (normalizeMetricStatus(status) === 'failed') {
    return '未通过'
  }
  return '不可用'
}

function metricTitle(metric: EvalMetricResultResponse) {
  if (metric.metric === 'evidence_faithfulness') {
    return '证据忠实度'
  }
  if (metric.metric === 'compare_consistency') {
    return '对比一致性'
  }
  if (metric.metric === 'memory_source_coverage') {
    return '记忆溯源覆盖率'
  }
  return metric.metric
}

function summarizeDetails(details?: Record<string, unknown> | null) {
  if (!details) {
    return null
  }

  const value = JSON.stringify(details, null, 2)
  return value.length > 320 ? `${value.slice(0, 320)}...` : value
}

export default function AdminEvalsPage() {
  const searchParams = useSearchParams()
  const requestedProjectId = searchParams.get('projectId')
  const requestedJobId = searchParams.get('jobId')
  const [projectId, setProjectId] = useState('')
  const [threadId, setThreadId] = useState(AUTO_VALUE)
  const [compareId, setCompareId] = useState(AUTO_VALUE)
  const [activeJobId, setActiveJobId] = useState<string>()

  const {
    data: projects = [],
    isLoading: projectsLoading,
    error: projectsError,
  } = useProjects(false)
  const {
    data: threads = [],
    error: threadsError,
  } = useProjectThreads(projectId)
  const {
    data: compares = [],
    error: comparesError,
  } = useProjectCompares(projectId)
  const {
    data: evalJobs = [],
    isLoading: jobsLoading,
    error: jobsError,
  } = useProjectEvalJobs()
  const {
    data: activeJob,
    isLoading: activeJobLoading,
  } = useProjectEvalJob(activeJobId)
  const runProjectEval = useRunProjectEval()

  useEffect(() => {
    if (projects.length === 0) {
      return
    }

    const requestedExists = requestedProjectId
      ? projects.some((project) => project.id === requestedProjectId)
      : false
    if (requestedExists && requestedProjectId) {
      setProjectId((current) => current || requestedProjectId)
      return
    }

    if (projectId && projects.some((project) => project.id === projectId)) {
      return
    }

    const demoProject = projects.find((project) => /demo|智研舱/i.test(project.name))
    setProjectId(demoProject?.id || projects[0].id)
  }, [projectId, projects, requestedProjectId])

  useEffect(() => {
    setThreadId(AUTO_VALUE)
    setCompareId(AUTO_VALUE)
  }, [projectId])

  const projectJobs = useMemo(() => {
    if (!projectId) {
      return []
    }
    return evalJobs.filter((job) => readProjectIdFromEvalJob(job) === projectId)
  }, [evalJobs, projectId])

  useEffect(() => {
    if (requestedJobId && projectJobs.some((job) => job.job_id === requestedJobId)) {
      if (activeJobId !== requestedJobId) {
        setActiveJobId(requestedJobId)
      }
      return
    }

    if (activeJobId && projectJobs.some((job) => job.job_id === activeJobId)) {
      return
    }

    if (projectJobs.length > 0) {
      setActiveJobId(projectJobs[0].job_id)
      return
    }

    if (activeJobId) {
      setActiveJobId(undefined)
    }
  }, [activeJobId, projectJobs, requestedJobId])

  const evalOutput = readProjectEvalOutput(activeJob)

  const handleRunEval = async () => {
    if (!projectId) {
      return
    }

    try {
      const response = await runProjectEval.mutateAsync({
        project_id: projectId,
        thread_id: threadId === AUTO_VALUE ? undefined : threadId,
        compare_id: compareId === AUTO_VALUE ? undefined : compareId,
      })
      setActiveJobId(response.job_id)
    } catch {}
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
          <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="outline">run_project_eval</Badge>
                <Badge variant="secondary">最小评测</Badge>
              </div>
              <div className="space-y-1">
                <h1 className="text-3xl font-semibold tracking-tight">评测中心</h1>
                <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
                  用一组最小指标检查当前项目的证据引用、对比结构和记忆溯源是否已经可演示。
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline">
                <Link href="/admin/jobs">打开任务队列</Link>
              </Button>
              <Button
                onClick={() => {
                  void handleRunEval()
                }}
                disabled={!projectId || runProjectEval.isPending}
              >
                {runProjectEval.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    正在提交评测...
                  </>
                ) : (
                  '运行最小评测'
                )}
              </Button>
            </div>
          </header>

          {projectsError ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>项目列表加载失败</AlertTitle>
              <AlertDescription>{formatApiError(projectsError)}</AlertDescription>
            </Alert>
          ) : null}

          {jobsError ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>评测任务列表加载失败</AlertTitle>
              <AlertDescription>{formatApiError(jobsError)}</AlertDescription>
            </Alert>
          ) : null}

          {runProjectEval.error ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>评测任务提交失败</AlertTitle>
              <AlertDescription>{formatApiError(runProjectEval.error)}</AlertDescription>
            </Alert>
          ) : null}

          {projectsLoading ? (
            <div className="flex min-h-[18rem] items-center justify-center rounded-lg border border-dashed border-border/70">
              <LoadingSpinner size="lg" />
            </div>
          ) : projects.length === 0 ? (
            <Card className="border-dashed border-border/70">
              <CardContent className="py-12">
                <EmptyState
                  icon={ClipboardList}
                  title="还没有项目可评测"
                  description="先创建项目或准备 Demo 项目，再回来运行最小评测。"
                  action={
                    <Button asChild>
                      <Link href="/projects">去项目页</Link>
                    </Button>
                  }
                />
              </CardContent>
            </Card>
          ) : (
            <>
              <Card className="border-border/70">
                <CardHeader>
                  <CardTitle>评测范围</CardTitle>
                  <CardDescription>
                    不指定 thread 或 compare 时，会默认取当前项目最新的一条问答和最近完成的对比结果。
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <div className="text-sm font-medium">项目</div>
                    <Select value={projectId} onValueChange={setProjectId}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="选择项目" />
                      </SelectTrigger>
                      <SelectContent>
                        {projects.map((project) => (
                          <SelectItem key={project.id} value={project.id}>
                            {project.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <div className="text-sm font-medium">问答线程</div>
                    <Select value={threadId} onValueChange={setThreadId} disabled={!projectId}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="自动选择最新线程" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={AUTO_VALUE}>自动选择最新线程</SelectItem>
                        {threads.map((thread) => (
                          <SelectItem key={thread.id} value={thread.id}>
                            {thread.title}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <div className="text-sm font-medium">对比结果</div>
                    <Select value={compareId} onValueChange={setCompareId} disabled={!projectId}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="自动选择最近完成态对比" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={AUTO_VALUE}>自动选择最近完成态对比</SelectItem>
                        {compares.map((compare) => (
                          <SelectItem key={compare.id} value={compare.id}>
                            {compare.source_a_title} / {compare.source_b_title}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>

              {threadsError ? (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>问答线程加载失败</AlertTitle>
                  <AlertDescription>{formatApiError(threadsError)}</AlertDescription>
                </Alert>
              ) : null}

              {comparesError ? (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>对比列表加载失败</AlertTitle>
                  <AlertDescription>{formatApiError(comparesError)}</AlertDescription>
                </Alert>
              ) : null}

              <div className="grid gap-4 md:grid-cols-3">
                <Card className="border-border/70">
                  <CardHeader>
                    <CardTitle>线程候选</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-semibold">{threads.length}</div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      {threadId === AUTO_VALUE ? '当前使用自动选择。' : `已指定线程 ${threadId}。`}
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-border/70">
                  <CardHeader>
                    <CardTitle>对比候选</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-semibold">{compares.length}</div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      {compareId === AUTO_VALUE ? '当前使用自动选择。' : `已指定对比 ${compareId}。`}
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-border/70">
                  <CardHeader>
                    <CardTitle>最近评测任务</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-semibold">
                      {jobsLoading ? '...' : projectJobs.length}
                    </div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      当前项目最近完成的评测会显示在下方。
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Card className="border-border/70">
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <CardTitle>当前任务</CardTitle>
                      <CardDescription>
                        提交后会自动轮询状态。完成时，下面会直接显示评测结果。
                      </CardDescription>
                    </div>
                    {activeJob?.status ? (
                      <Badge variant="outline">{activeJob.status}</Badge>
                    ) : null}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {activeJobLoading ? (
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                      <LoadingSpinner size="sm" />
                      正在获取评测状态...
                    </div>
                  ) : activeJob ? (
                    <>
                      <div className="grid gap-3 md:grid-cols-3">
                        <div className="rounded-md border border-border/70 p-3">
                          <div className="text-xs text-muted-foreground">job_id</div>
                          <div className="mt-1 break-all text-sm font-medium">{activeJob.job_id}</div>
                        </div>
                        <div className="rounded-md border border-border/70 p-3">
                          <div className="text-xs text-muted-foreground">创建时间</div>
                          <div className="mt-1 text-sm font-medium">
                            {formatProjectTimestamp(activeJob.created)}
                          </div>
                        </div>
                        <div className="rounded-md border border-border/70 p-3">
                          <div className="text-xs text-muted-foreground">完成时间</div>
                          <div className="mt-1 text-sm font-medium">
                            {formatProjectTimestamp(activeJob.completed_at || activeJob.updated)}
                          </div>
                        </div>
                      </div>

                      {activeJob.error_message ? (
                        <Alert variant="destructive">
                          <AlertCircle className="h-4 w-4" />
                          <AlertTitle>评测执行失败</AlertTitle>
                          <AlertDescription>{activeJob.error_message}</AlertDescription>
                        </Alert>
                      ) : null}

                      {!evalOutput && (
                        <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                          {activeJob.status === 'queued' || activeJob.status === 'running'
                            ? '任务已经入队，正在等待结果。'
                            : '这条任务还没有可展示的评测结果。'}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                      还没有选中的评测任务。
                    </div>
                  )}
                </CardContent>
              </Card>

              {evalOutput ? (
                <>
                  <Card className="border-border/70">
                    <CardHeader>
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <CardTitle>评测结果</CardTitle>
                          <CardDescription>{evalOutput.summary}</CardDescription>
                        </div>
                        <Badge variant={evalOutput.passed_metrics === evalOutput.available_metrics ? 'default' : 'secondary'}>
                          {evalOutput.passed_metrics}/{evalOutput.available_metrics}
                        </Badge>
                      </div>
                    </CardHeader>
                  </Card>

                  <div className="grid gap-4 md:grid-cols-3">
                    {evalOutput.metrics.map((metric) => {
                      const detailsText = summarizeDetails(metric.details)

                      return (
                          <Card key={metric.metric} className="border-border/70">
                          <CardHeader className="space-y-3">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <CardTitle className="text-base">{metricTitle(metric)}</CardTitle>
                                <CardDescription>{metric.metric}</CardDescription>
                              </div>
                              <Badge variant={metricBadgeVariant(metric.status)}>
                                {metricLabel(metric.status)}
                              </Badge>
                            </div>
                            <div className="text-sm text-muted-foreground">{metric.summary}</div>
                          </CardHeader>
                          <CardContent className="space-y-3">
                            {(() => {
                              const normalizedStatus = normalizeMetricStatus(String(metric.status))

                              return (
                            <div className="flex items-center gap-2 text-sm">
                              {normalizedStatus === 'passed' ? (
                                <CheckCircle2 className="h-4 w-4 text-green-600" />
                              ) : normalizedStatus === 'failed' ? (
                                <ShieldAlert className="h-4 w-4 text-destructive" />
                              ) : (
                                <AlertCircle className="h-4 w-4 text-muted-foreground" />
                              )}
                              <span>
                                score {metric.score ?? '-'}
                                {metric.threshold !== undefined && metric.threshold !== null
                                  ? ` / threshold ${metric.threshold}`
                                  : ''}
                              </span>
                            </div>
                              )
                            })()}
                            {detailsText ? (
                              <pre className="overflow-x-auto rounded-md border border-border/70 bg-muted/30 p-3 text-[11px] leading-5">
                                {detailsText}
                              </pre>
                            ) : (
                              <div className="rounded-md border border-dashed border-border/70 p-3 text-sm text-muted-foreground">
                                没有额外明细。
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      )
                    })}
                  </div>
                </>
              ) : null}

              <Card className="border-border/70">
                <CardHeader>
                  <CardTitle>当前项目最近评测</CardTitle>
                  <CardDescription>
                    这里只显示已经有结果、且能关联到当前项目的评测任务。
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {projectJobs.length === 0 ? (
                    <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                      还没有最近评测记录。
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {projectJobs.slice(0, 6).map((job) => {
                        const output = readProjectEvalOutput(job)
                        return (
                          <button
                            key={job.job_id}
                            type="button"
                            className="w-full rounded-md border border-border/70 p-3 text-left transition-colors hover:bg-muted/30"
                            onClick={() => {
                              setActiveJobId(job.job_id)
                            }}
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="text-sm font-medium">{job.job_id}</div>
                              <Badge variant="outline">{job.status}</Badge>
                            </div>
                            <div className="mt-2 text-sm text-muted-foreground">
                              {output?.summary || '这条任务还没有可展示的结果。'}
                            </div>
                            <div className="mt-2 text-xs text-muted-foreground">
                              {formatProjectTimestamp(job.completed_at || job.updated)}
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </AppShell>
  )
}
