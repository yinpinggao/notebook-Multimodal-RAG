import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ProjectCompareRecordResponse } from '@/lib/types/api'

const MODE_LABELS = {
  general: '综合对比',
  requirements: '要求对比',
  risks: '风险对比',
  timeline: '时间线对比',
}

export function CompareSummary({ compare }: { compare: ProjectCompareRecordResponse }) {
  const result = compare.result

  return (
    <Card className="border-border/70">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle>对比摘要</CardTitle>
          <Badge variant="outline">{MODE_LABELS[compare.compare_mode]}</Badge>
          <Badge variant="outline">{compare.status}</Badge>
        </div>
        <CardDescription>
          {compare.source_a_title} vs {compare.source_b_title}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <p className="text-sm leading-6 text-foreground">
          {result?.summary || '对比任务已创建，结果生成后会出现在这里。'}
        </p>

        {result ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <div className="rounded-md border border-border/70 p-3">
              <div className="text-xs text-muted-foreground">共同点</div>
              <div className="mt-1 text-2xl font-semibold">{result.similarities.length}</div>
            </div>
            <div className="rounded-md border border-border/70 p-3">
              <div className="text-xs text-muted-foreground">差异点</div>
              <div className="mt-1 text-2xl font-semibold">{result.differences.length}</div>
            </div>
            <div className="rounded-md border border-border/70 p-3">
              <div className="text-xs text-muted-foreground">冲突点</div>
              <div className="mt-1 text-2xl font-semibold">{result.conflicts.length}</div>
            </div>
            <div className="rounded-md border border-border/70 p-3">
              <div className="text-xs text-muted-foreground">缺失点</div>
              <div className="mt-1 text-2xl font-semibold">{result.missing_items.length}</div>
            </div>
            <div className="rounded-md border border-border/70 p-3">
              <div className="text-xs text-muted-foreground">人工复核</div>
              <div className="mt-1 text-2xl font-semibold">
                {result.human_review_required.length}
              </div>
            </div>
          </div>
        ) : null}

        {compare.error_message ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
            {compare.error_message}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
