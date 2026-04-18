import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function ProjectOutputsPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>输出工坊</CardTitle>
        <CardDescription>
          这里会沉淀综述、差异报告、答辩提纲、问题卡片等产物。当前先完成 routes 和命名切换。
        </CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        产物生成后续会复用现有 transformations / podcast / markdown 编辑能力，不会平地起一套新编辑器。
      </CardContent>
    </Card>
  )
}
