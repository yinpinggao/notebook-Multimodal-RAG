'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { AlertCircle, Workflow } from 'lucide-react'

import { RunDetail } from '@/components/runs/run-detail'
import { RunList } from '@/components/runs/run-list'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useProjectRun, useProjectRuns } from '@/lib/hooks/use-project-runs'
import { projectIdToNotebookId } from '@/lib/project-alias'
import { formatApiError } from '@/lib/utils/error-handler'

export default function ProjectRunsPage() {
  const params = useParams()
  const routeProjectId = params?.projectId ? String(params.projectId) : ''
  const projectId = projectIdToNotebookId(routeProjectId)

  const [activeRunId, setActiveRunId] = useState<string | null>(null)

  const {
    data: runs = [],
    isLoading: runsLoading,
    error: runsError,
  } = useProjectRuns(projectId)
  const {
    data: activeRun,
    isLoading: activeRunLoading,
    error: activeRunError,
  } = useProjectRun(projectId, activeRunId || undefined)

  useEffect(() => {
    if (!runs.length) {
      setActiveRunId(null)
      return
    }

    if (!activeRunId || !runs.some((run) => run.id === activeRunId)) {
      setActiveRunId(runs[0].id)
    }
  }, [activeRunId, runs])

  const counts = useMemo(
    () => ({
      total: runs.length,
      running: runs.filter((run) => run.status === 'queued' || run.status === 'running').length,
      failed: runs.filter((run) => run.status === 'failed').length,
    }),
    [runs]
  )

  const topLevelError = runsError || activeRunError

  return (
    <div className="space-y-6">
      <Card className="border-border/70">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Workflow className="h-4 w-4 text-muted-foreground" />
            <CardTitle>运行轨迹</CardTitle>
          </div>
          <CardDescription>
            把 ask、compare、artifact 和记忆重建留下来的执行轨迹摊开看，先看步骤，再看证据、工具和写入结果。
          </CardDescription>
        </CardHeader>
      </Card>

      {topLevelError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>运行轨迹暂时不可用</AlertTitle>
          <AlertDescription>{formatApiError(topLevelError)}</AlertDescription>
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">{counts.total} 条运行</Badge>
        <Badge variant="secondary">{counts.running} 条进行中</Badge>
        <Badge variant="outline">{counts.failed} 条失败</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <RunList
          runs={runs}
          activeRunId={activeRunId}
          isLoading={runsLoading}
          onSelect={setActiveRunId}
        />

        <RunDetail
          run={activeRun ?? runs.find((run) => run.id === activeRunId) ?? null}
          isLoading={activeRunLoading}
        />
      </div>
    </div>
  )
}
