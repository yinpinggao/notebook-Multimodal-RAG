'use client'

import { BrainCircuit } from 'lucide-react'

import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MemoryRecordResponse } from '@/lib/types/api'

import { MemoryCard } from './memory-card'

interface MemoryListProps {
  memories: MemoryRecordResponse[]
  isLoading?: boolean
  isUpdating?: boolean
  isDeleting?: boolean
  onAccept: (memory: MemoryRecordResponse) => void
  onReview: (memory: MemoryRecordResponse) => void
  onDelete: (memory: MemoryRecordResponse) => void
}

function buildSections(memories: MemoryRecordResponse[]) {
  return [
    {
      title: '待确认记忆',
      items: memories.filter((memory) => memory.status === 'draft'),
    },
    {
      title: '术语定义',
      items: memories.filter(
        (memory) => memory.type === 'term' && memory.status === 'accepted'
      ),
    },
    {
      title: '已确认事实',
      items: memories.filter(
        (memory) => memory.type === 'fact' && memory.status === 'accepted'
      ),
    },
    {
      title: '风险项',
      items: memories.filter(
        (memory) => memory.type === 'risk' && memory.status === 'accepted'
      ),
    },
    {
      title: '历史决策 / 偏好',
      items: memories.filter(
        (memory) =>
          ['decision', 'preference'].includes(memory.type) &&
          memory.status === 'accepted'
      ),
    },
    {
      title: '冻结 / 过时',
      items: memories.filter((memory) =>
        ['frozen', 'deprecated'].includes(memory.status)
      ),
    },
  ].filter((section) => section.items.length > 0)
}

export function MemoryList({
  memories,
  isLoading = false,
  isUpdating = false,
  isDeleting = false,
  onAccept,
  onReview,
  onDelete,
}: MemoryListProps) {
  const sections = buildSections(memories)

  return (
    <Card className="border-border/70">
      <CardHeader>
        <div className="flex items-center gap-2">
          <BrainCircuit className="h-4 w-4 text-muted-foreground" />
          <CardTitle>记忆列表</CardTitle>
        </div>
        <CardDescription>
          先把自动抽出来的记忆过一遍。长期记忆必须带来源，确认后再留下。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {isLoading ? (
          <div className="flex min-h-60 items-center justify-center">
            <LoadingSpinner size="lg" />
          </div>
        ) : memories.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
            还没有项目长期记忆。可以先触发一次重建，把结构化事实拉进治理流程。
          </div>
        ) : (
          sections.map((section) => (
            <section key={section.title} className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold">{section.title}</h3>
                <span className="text-xs text-muted-foreground">
                  {section.items.length} 条
                </span>
              </div>

              <div className="space-y-3">
                {section.items.map((memory) => (
                  <MemoryCard
                    key={memory.id}
                    memory={memory}
                    isUpdating={isUpdating}
                    isDeleting={isDeleting}
                    onAccept={onAccept}
                    onReview={onReview}
                    onDelete={onDelete}
                  />
                ))}
              </div>
            </section>
          ))
        )}
      </CardContent>
    </Card>
  )
}
