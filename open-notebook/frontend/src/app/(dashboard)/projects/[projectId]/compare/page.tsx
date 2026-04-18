import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function ProjectComparePage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>对比中心</CardTitle>
        <CardDescription>
          这里会承接文档对比、版本对比、规则对方案等工作流。当前先建立导航入口和页面骨架。
        </CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        后续 Compare 服务会复用现有 source、summary、Visual RAG/检索结果，而不是重写一套底层文档系统。
      </CardContent>
    </Card>
  )
}
