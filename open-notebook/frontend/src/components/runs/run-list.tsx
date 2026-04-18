import { AgentRunResponse } from '@/lib/types/api'

import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface RunListProps {
  runs: AgentRunResponse[]
  activeRunId: string | null
  isLoading?: boolean
  onSelect: (runId: string) => void
}

function statusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'completed') return 'default'
  if (status === 'failed') return 'destructive'
  if (status === 'running') return 'secondary'
  return 'outline'
}

export function RunList({ runs, activeRunId, isLoading = false, onSelect }: RunListProps) {
  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle>运行列表</CardTitle>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="flex min-h-40 items-center justify-center">
            <LoadingSpinner size="lg" />
          </div>
        ) : !runs.length ? (
          <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
            还没有运行记录。
          </div>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => (
              <button
                key={run.id}
                type="button"
                onClick={() => onSelect(run.id)}
                className={cn(
                  'w-full rounded-md border border-border/70 p-3 text-left transition-colors',
                  activeRunId === run.id ? 'bg-muted/40' : 'hover:bg-muted/20'
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
                  <Badge variant="outline">{run.run_type}</Badge>
                  {run.selected_skill ? <Badge variant="secondary">{run.selected_skill}</Badge> : null}
                </div>

                <div className="mt-2 text-sm font-medium">{run.input_summary || run.run_type}</div>
                <div className="mt-1 text-xs text-muted-foreground">{run.id}</div>
                <div className="mt-2 text-xs text-muted-foreground">
                  {run.completed_at || run.started_at || run.created_at}
                </div>
              </button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
