'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { AlertCircle } from 'lucide-react'

import { DetailSplitLayout, PageHeader } from '@/components/projects/page-templates'
import { RunDetail } from '@/components/runs/run-detail'
import { RunList } from '@/components/runs/run-list'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
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
      <PageHeader
        eyebrow={<Badge variant="outline">Runs / Trace</Badge>}
        title="运行轨迹"
        description="把 ask、compare、artifact 和记忆重建留下来的执行轨迹摊开看。"
      />

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

      <DetailSplitLayout
        rail={
          <RunList
            runs={runs}
            activeRunId={activeRunId}
            isLoading={runsLoading}
            onSelect={setActiveRunId}
          />
        }
        detail={
          <RunDetail
            run={activeRun ?? runs.find((run) => run.id === activeRunId) ?? null}
            isLoading={activeRunLoading}
          />
        }
        railTitle="运行列表"
        railDescription="先选一条运行，再看步骤、工具和写入结果。"
        railBadge={<Badge variant="outline">{runs.length}</Badge>}
        railWidth="minmax(320px, 0.9fr)"
        detailWidth="minmax(0, 1.55fr)"
      />
    </div>
  )
}
