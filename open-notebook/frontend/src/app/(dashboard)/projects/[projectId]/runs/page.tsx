import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function ProjectRunsPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>运行轨迹</CardTitle>
        <CardDescription>
          这里会展示 run trace、tool calls、evidence reads、memory writes 和 outputs。当前先占住产品入口。
        </CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        后续会把 ask、compare、artifact 等任务统一写入 run 记录，而不只保留 Visual RAG 的局部会话痕迹。
      </CardContent>
    </Card>
  )
}
