import { Hash, Tags } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface TopicClusterCardProps {
  topics: string[]
  keywords: string[]
}

export function TopicClusterCard({
  topics,
  keywords,
}: TopicClusterCardProps) {
  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle>核心主题与术语</CardTitle>
        <CardDescription>
          把资料里的主题簇和高频概念先收拢起来，方便继续追问和写综述。
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Hash className="h-4 w-4 text-muted-foreground" />
            主题簇
          </div>
          <div className="flex flex-wrap gap-2">
            {topics.map((topic) => (
              <Badge key={topic} variant="secondary" className="px-3 py-1">
                {topic}
              </Badge>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Tags className="h-4 w-4 text-muted-foreground" />
            关键词
          </div>
          <div className="flex flex-wrap gap-2">
            {keywords.map((keyword) => (
              <Badge key={keyword} variant="outline" className="px-3 py-1">
                {keyword}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
