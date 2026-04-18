import { AgentStepResponse } from '@/lib/types/api'

interface ToolCallCardProps {
  step: AgentStepResponse
}

function renderJsonBlock(value?: Record<string, unknown> | null) {
  if (!value || Object.keys(value).length === 0) {
    return null
  }

  return (
    <pre className="overflow-x-auto rounded-md border border-border/70 bg-muted/30 p-3 text-xs leading-6">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}

export function ToolCallCard({ step }: ToolCallCardProps) {
  return (
    <div className="space-y-3 rounded-md border border-border/70 p-3">
      <div className="text-sm font-medium">{step.tool_name || step.title}</div>

      {step.input_json ? (
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">input</div>
          {renderJsonBlock(step.input_json)}
        </div>
      ) : null}

      {step.output_json ? (
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">output</div>
          {renderJsonBlock(step.output_json)}
        </div>
      ) : null}

      {step.error ? <div className="text-xs text-destructive">{step.error}</div> : null}
    </div>
  )
}
