import { Clock3 } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ProjectTimelineEvent,
  formatProjectTimestamp,
} from '@/lib/project-workspace'

interface TimelineCardProps {
  events: ProjectTimelineEvent[]
}

export function TimelineCard({ events }: TimelineCardProps) {
  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle>项目时间线</CardTitle>
        <CardDescription>
          让你快速看到项目从创建、整理到索引准备的大致节奏。
        </CardDescription>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {events.map((event, index) => (
            <div key={event.id} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div className="flex h-8 w-8 items-center justify-center rounded-full border border-border/70 bg-muted/40">
                  <Clock3 className="h-4 w-4 text-muted-foreground" />
                </div>
                {index < events.length - 1 ? (
                  <div className="mt-2 h-full min-h-6 w-px bg-border" />
                ) : null}
              </div>

              <div className="space-y-1 pb-2">
                <div className="text-sm font-medium">{event.title}</div>
                <div className="text-sm text-muted-foreground">{event.description}</div>
                <div className="text-xs text-muted-foreground">
                  {formatProjectTimestamp(event.occurredAt)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
