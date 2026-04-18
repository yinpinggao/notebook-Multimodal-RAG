'use client'

import Link from 'next/link'
import { useState } from 'react'
import { AlertCircle, ListOrdered, Loader2, RotateCcw, XCircle } from 'lucide-react'

import { EmptyState } from '@/components/common/EmptyState'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { AppShell } from '@/components/layout/AppShell'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { readProjectIdFromEvalJob } from '@/lib/hooks/use-admin-evals'
import {
  useCancelCommandJob,
  useCommandJobs,
  useRetryCommandJob,
} from '@/lib/hooks/use-admin-jobs'
import { formatProjectTimestamp } from '@/lib/project-workspace'
import { CommandJobListItemResponse } from '@/lib/types/api'
import { formatApiError } from '@/lib/utils/error-handler'

const ALL_STATUS = '__all__'

function jobBadgeVariant(status: string) {
  if (status === 'completed') {
    return 'default'
  }
  if (status === 'failed') {
    return 'destructive'
  }
  if (status === 'cancelled') {
    return 'secondary'
  }
  return 'outline'
}

function summarizeJobResult(job: CommandJobListItemResponse) {
  const result = job.result
  if (!result || typeof result !== 'object') {
    return null
  }

  if (typeof result.summary === 'string') {
    return result.summary
  }
  if (typeof result.message === 'string') {
    return result.message
  }

  const value = JSON.stringify(result)
  return value.length > 220 ? `${value.slice(0, 220)}...` : value
}

export default function AdminJobsPage() {
  const [commandFilter, setCommandFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState(ALL_STATUS)
  const retryJob = useRetryCommandJob()
  const cancelJob = useCancelCommandJob()
  const {
    data: jobs = [],
    isLoading,
    error,
  } = useCommandJobs({
    commandFilter: commandFilter.trim() || undefined,
    statusFilter: statusFilter === ALL_STATUS ? undefined : statusFilter,
    limit: 60,
  })

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
          <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="outline">commands/jobs</Badge>
                <Badge variant="secondary">后台队列</Badge>
              </div>
              <div className="space-y-1">
                <h1 className="text-3xl font-semibold tracking-tight">任务队列</h1>
                <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
                  看清后台命令现在做到哪一步。失败原因、重试次数和最近结果都在这里。
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline">
                <Link href="/admin/evals">打开评测中心</Link>
              </Button>
            </div>
          </header>

          <Card className="border-border/70">
            <CardHeader>
              <CardTitle>筛选</CardTitle>
              <CardDescription>按命令名和状态筛选最近的后台任务。</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
              <div className="space-y-2">
                <div className="text-sm font-medium">command_name</div>
                <Input
                  value={commandFilter}
                  onChange={(event) => setCommandFilter(event.target.value)}
                  placeholder="例如 run_project_eval"
                />
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">status</div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="全部状态" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_STATUS}>全部状态</SelectItem>
                    <SelectItem value="queued">queued</SelectItem>
                    <SelectItem value="running">running</SelectItem>
                    <SelectItem value="completed">completed</SelectItem>
                    <SelectItem value="failed">failed</SelectItem>
                    <SelectItem value="cancelled">cancelled</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {error ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>任务列表加载失败</AlertTitle>
              <AlertDescription>{formatApiError(error)}</AlertDescription>
            </Alert>
          ) : null}

          {retryJob.error ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>任务重试失败</AlertTitle>
              <AlertDescription>{formatApiError(retryJob.error)}</AlertDescription>
            </Alert>
          ) : null}

          {cancelJob.error ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>取消任务失败</AlertTitle>
              <AlertDescription>{formatApiError(cancelJob.error)}</AlertDescription>
            </Alert>
          ) : null}

          {isLoading ? (
            <div className="flex min-h-[18rem] items-center justify-center rounded-lg border border-dashed border-border/70">
              <LoadingSpinner size="lg" />
            </div>
          ) : jobs.length === 0 ? (
            <Card className="border-dashed border-border/70">
              <CardContent className="py-12">
                <EmptyState
                  icon={ListOrdered}
                  title="没有匹配的任务"
                  description="换一个状态筛选，或者先去运行一次评测。"
                  action={
                    <Button asChild>
                      <Link href="/admin/evals">去运行评测</Link>
                    </Button>
                  }
                />
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {jobs.map((job) => {
                const resultSummary = summarizeJobResult(job)
                const evalProjectId = readProjectIdFromEvalJob(job)
                const canRetry = job.status === 'failed' || job.status === 'cancelled'
                const canCancel = job.status === 'queued' || job.status === 'running'

                return (
                  <Card key={job.job_id} className="border-border/70">
                    <CardHeader className="space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="space-y-1">
                          <CardTitle className="text-base">
                            {job.app_name}.{job.command_name}
                          </CardTitle>
                          <CardDescription className="break-all">{job.job_id}</CardDescription>
                        </div>
                        <Badge variant={jobBadgeVariant(job.status)}>{job.status}</Badge>
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-4">
                      <div className="grid gap-3 md:grid-cols-4">
                        <div className="rounded-md border border-border/70 p-3">
                          <div className="text-xs text-muted-foreground">创建时间</div>
                          <div className="mt-1 text-sm font-medium">
                            {formatProjectTimestamp(job.created)}
                          </div>
                        </div>
                        <div className="rounded-md border border-border/70 p-3">
                          <div className="text-xs text-muted-foreground">开始时间</div>
                          <div className="mt-1 text-sm font-medium">
                            {formatProjectTimestamp(job.started_at)}
                          </div>
                        </div>
                        <div className="rounded-md border border-border/70 p-3">
                          <div className="text-xs text-muted-foreground">完成时间</div>
                          <div className="mt-1 text-sm font-medium">
                            {formatProjectTimestamp(job.completed_at)}
                          </div>
                        </div>
                        <div className="rounded-md border border-border/70 p-3">
                          <div className="text-xs text-muted-foreground">重试次数</div>
                          <div className="mt-1 text-sm font-medium">{job.retry_count}</div>
                        </div>
                      </div>

                      {job.error_message ? (
                        <Alert variant="destructive">
                          <AlertCircle className="h-4 w-4" />
                          <AlertTitle>失败原因</AlertTitle>
                          <AlertDescription>{job.error_message}</AlertDescription>
                        </Alert>
                      ) : null}

                      {resultSummary ? (
                        <div className="rounded-md border border-border/70 p-3">
                          <div className="text-xs text-muted-foreground">结果摘要</div>
                          <div className="mt-1 text-sm leading-6">{resultSummary}</div>
                        </div>
                      ) : null}

                      <div className="flex flex-wrap gap-2">
                        {canRetry ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              void retryJob.mutateAsync(job.job_id)
                            }}
                            disabled={retryJob.isPending}
                          >
                            {retryJob.isPending ? (
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <RotateCcw className="mr-2 h-4 w-4" />
                            )}
                            重新提交
                          </Button>
                        ) : null}

                        {canCancel ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              void cancelJob.mutateAsync(job.job_id)
                            }}
                            disabled={cancelJob.isPending}
                          >
                            {cancelJob.isPending ? (
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <XCircle className="mr-2 h-4 w-4" />
                            )}
                            取消任务
                          </Button>
                        ) : null}

                        {job.command_name === 'run_project_eval' && evalProjectId ? (
                          <Button asChild size="sm" variant="outline">
                            <Link
                              href={`/admin/evals?projectId=${encodeURIComponent(evalProjectId)}&jobId=${encodeURIComponent(job.job_id)}`}
                            >
                              查看评测
                            </Link>
                          </Button>
                        ) : null}
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
