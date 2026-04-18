'use client'

import { AlertTriangle } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MemoryRecordResponse } from '@/lib/types/api'

interface MemoryConflictPanelProps {
  memories: MemoryRecordResponse[]
}

function buildConflictGroups(memories: MemoryRecordResponse[]) {
  const groups = new Map<string, MemoryRecordResponse[]>()

  memories.forEach((memory) => {
    if (!memory.conflict_group) {
      return
    }

    const currentGroup = groups.get(memory.conflict_group) || []
    currentGroup.push(memory)
    groups.set(memory.conflict_group, currentGroup)
  })

  return [...groups.entries()].filter(([, items]) => items.length > 1)
}

export function MemoryConflictPanel({ memories }: MemoryConflictPanelProps) {
  const conflictGroups = buildConflictGroups(memories)

  return (
    <Card className="border-border/70">
      <CardHeader>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          <CardTitle>冲突组</CardTitle>
        </div>
        <CardDescription>
          第一版只展示已有 conflict group。复杂合并留到后面。
        </CardDescription>
      </CardHeader>
      <CardContent>
        {conflictGroups.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
            当前还没有检测到需要人工合并的冲突组。
          </div>
        ) : (
          <div className="space-y-4">
            {conflictGroups.map(([groupId, items]) => (
              <div key={groupId} className="rounded-md border border-border/70 p-4">
                <div className="text-sm font-medium">{groupId}</div>
                <div className="mt-3 space-y-2">
                  {items.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-md border border-border/70 px-3 py-3 text-sm leading-6"
                    >
                      {item.text}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
