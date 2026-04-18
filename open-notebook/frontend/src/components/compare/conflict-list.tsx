import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ProjectCompareRecordResponse } from '@/lib/types/api'

export function ConflictList({ compare }: { compare: ProjectCompareRecordResponse }) {
  const conflicts = compare.result?.conflicts || []

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle>冲突项</CardTitle>
        <CardDescription>优先回看的，是这些时间、数字或约束表述不一致的地方。</CardDescription>
      </CardHeader>

      <CardContent>
        {conflicts.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
            当前没有检测到明显的冲突项。
          </div>
        ) : (
          <div className="space-y-3">
            {conflicts.map((item, index) => (
              <div
                key={`${item.title}-${index}`}
                className="rounded-md border border-border/70 p-3"
              >
                <div className="text-sm font-medium leading-6">{item.title}</div>
                <div className="mt-1 break-words text-sm text-muted-foreground">
                  {item.detail}
                </div>
                {item.source_refs.length > 0 ? (
                  <div className="mt-2 text-xs text-muted-foreground">
                    refs: {item.source_refs.join(', ')}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
