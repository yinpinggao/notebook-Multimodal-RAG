import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function ProjectOverviewPage() {
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>项目总览</CardTitle>
          <CardDescription>
            这是新的项目首页骨架。后续会在这里接入 overview 聚合 API、项目画像、风险、时间线和最近产物。
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          当前阶段只先建立 Project Workspace 的信息架构，不在这里实现真实 overview 聚合逻辑。
        </CardContent>
      </Card>
    </>
  )
}
