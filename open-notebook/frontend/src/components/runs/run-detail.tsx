import { AgentRunResponse } from '@/lib/types/api'

import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { StepTimeline } from '@/components/runs/step-timeline'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface RunDetailProps {
  run: AgentRunResponse | null
  isLoading?: boolean
}

function statusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'completed') return 'default'
  if (status === 'failed') return 'destructive'
  if (status === 'running') return 'secondary'
  return 'outline'
}

function renderValueList(values: string[]) {
  if (!values.length) {
    return <div className="text-sm text-muted-foreground">暂无</div>
  }

  return (
    <div className="flex flex-wrap gap-2">
      {values.slice(0, 8).map((value) => (
        <span key={value} className="rounded-md border border-border/70 px-2 py-1 text-xs">
          {value}
        </span>
      ))}
    </div>
  )
}

export function RunDetail({ run, isLoading = false }: RunDetailProps) {
  if (isLoading) {
    return (
      <div className="flex min-h-[24rem] items-center justify-center rounded-lg border border-dashed border-border/70">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!run) {
    return (
      <div className="rounded-lg border border-dashed border-border/70 p-6 text-sm text-muted-foreground">
        先从左侧选择一条运行。
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Card className="border-border/70">
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>{run.input_summary || run.run_type}</CardTitle>
            <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
            <Badge variant="outline">{run.run_type}</Badge>
            {run.selected_skill ? <Badge variant="secondary">{run.selected_skill}</Badge> : null}
          </div>
        </CardHeader>

        <CardContent className="space-y-4 text-sm">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <div className="text-xs text-muted-foreground">run_id</div>
              <div className="font-mono text-xs">{run.id}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">created_at</div>
              <div>{run.created_at}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">started_at</div>
              <div>{run.started_at || '未开始'}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">completed_at</div>
              <div>{run.completed_at || '进行中'}</div>
            </div>
          </div>

          {run.input_json ? (
            <pre className="overflow-x-auto rounded-md border border-border/70 bg-muted/30 p-3 text-xs leading-6">
              {JSON.stringify(run.input_json, null, 2)}
            </pre>
          ) : null}

          {run.output_json ? (
            <pre className="overflow-x-auto rounded-md border border-border/70 bg-muted/30 p-3 text-xs leading-6">
              {JSON.stringify(run.output_json, null, 2)}
            </pre>
          ) : null}

          {run.failure_reason ? (
            <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
              {run.failure_reason}
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">tool calls</div>
              {renderValueList(run.tool_calls)}
            </div>
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">evidence reads</div>
              {renderValueList(run.evidence_reads)}
            </div>
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">memory writes</div>
              {renderValueList(run.memory_writes)}
            </div>
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">outputs</div>
              {renderValueList(run.outputs)}
            </div>
          </div>
        </CardContent>
      </Card>

      <StepTimeline steps={run.steps} />
    </div>
  )
}
