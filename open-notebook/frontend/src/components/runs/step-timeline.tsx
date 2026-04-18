import { AgentStepResponse } from '@/lib/types/api'

import { ToolCallCard } from '@/components/runs/tool-call-card'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface StepTimelineProps {
  steps: AgentStepResponse[]
}

const STEP_LABELS: Record<string, string> = {
  plan: '规划',
  tool_call: '工具调用',
  evidence_read: '证据读取',
  memory_write: '记忆写入',
  artifact_write: '产物写入',
  answer: '回答',
  compare: '对比',
  system: '系统',
}

function statusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'completed') return 'default'
  if (status === 'failed') return 'destructive'
  if (status === 'running') return 'secondary'
  return 'outline'
}

function renderRefs(title: string, refs: string[]) {
  if (!refs.length) {
    return null
  }

  return (
    <div className="space-y-1">
      <div className="text-xs text-muted-foreground">{title}</div>
      <div className="flex flex-wrap gap-2">
        {refs.slice(0, 8).map((ref) => (
          <span key={ref} className="rounded-md border border-border/70 px-2 py-1 text-xs">
            {ref}
          </span>
        ))}
      </div>
    </div>
  )
}

export function StepTimeline({ steps }: StepTimelineProps) {
  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle>步骤轨迹</CardTitle>
      </CardHeader>

      <CardContent>
        {!steps.length ? (
          <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
            这条运行还没有记录步骤。
          </div>
        ) : (
          <div className="space-y-4">
            {steps.map((step) => (
              <div key={step.id} className="space-y-3 border-l border-border/70 pl-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">#{step.step_index + 1}</Badge>
                  <Badge variant={statusVariant(step.status)}>{step.status}</Badge>
                  <Badge variant="secondary">{STEP_LABELS[step.type] || step.type}</Badge>
                  <div className="text-sm font-medium">{step.title}</div>
                </div>

                {step.agent_name ? (
                  <div className="text-xs text-muted-foreground">{step.agent_name}</div>
                ) : null}

                {step.tool_name ? <ToolCallCard step={step} /> : null}

                {!step.tool_name && step.output_json ? (
                  <pre className="overflow-x-auto rounded-md border border-border/70 bg-muted/30 p-3 text-xs leading-6">
                    {JSON.stringify(step.output_json, null, 2)}
                  </pre>
                ) : null}

                {renderRefs('evidence', step.evidence_refs)}
                {renderRefs('memory', step.memory_refs)}
                {renderRefs('outputs', step.output_refs)}

                {step.error ? <div className="text-xs text-destructive">{step.error}</div> : null}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
