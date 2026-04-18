import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function ProjectMemoryPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>记忆中心</CardTitle>
        <CardDescription>
          这里会展示项目长期记忆、用户偏好记忆以及治理操作。当前版本仅保留新的产品信息架构入口。
        </CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        后续会在这个页面接入带 `source_refs` 的可审查记忆记录，而不是把记忆继续藏在隐式会话状态里。
      </CardContent>
    </Card>
  )
}
