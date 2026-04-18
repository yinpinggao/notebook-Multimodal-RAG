import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { CompareItemResponse, ProjectCompareRecordResponse } from '@/lib/types/api'

interface DiffRow {
  category: string
  item: CompareItemResponse
}

function buildRows(compare: ProjectCompareRecordResponse): DiffRow[] {
  const result = compare.result
  if (!result) {
    return []
  }

  return [
    ...result.similarities.map((item) => ({ category: '共同点', item })),
    ...result.differences.map((item) => ({ category: '差异点', item })),
    ...result.missing_items.map((item) => ({ category: '缺失点', item })),
    ...result.human_review_required.map((item) => ({ category: '人工复核', item })),
  ]
}

export function DiffTable({ compare }: { compare: ProjectCompareRecordResponse }) {
  const rows = buildRows(compare)

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle>结构化差异表</CardTitle>
        <CardDescription>把共同点、差异点、缺失项和人工复核项放到同一张表里看。</CardDescription>
      </CardHeader>

      <CardContent>
        {rows.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
            当前还没有可展示的结构化差异结果。
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full table-fixed border-collapse">
              <thead>
                <tr className="border-b border-border/70 text-left text-xs text-muted-foreground">
                  <th className="w-28 px-3 py-2 font-medium">类型</th>
                  <th className="w-56 px-3 py-2 font-medium">标题</th>
                  <th className="px-3 py-2 font-medium">说明</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr
                    key={`${row.category}-${row.item.title}-${index}`}
                    className="border-b border-border/50 align-top"
                  >
                    <td className="px-3 py-3 text-sm text-muted-foreground">{row.category}</td>
                    <td className="px-3 py-3 text-sm font-medium leading-6">{row.item.title}</td>
                    <td className="px-3 py-3 text-sm leading-6">
                      <div className="break-words">{row.item.detail}</div>
                      {row.item.source_refs.length > 0 ? (
                        <div className="mt-2 text-xs text-muted-foreground">
                          refs: {row.item.source_refs.join(', ')}
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
