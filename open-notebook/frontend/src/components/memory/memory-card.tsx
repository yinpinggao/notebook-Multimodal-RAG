'use client'

import { Archive, Check, Pencil, Trash2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card'
import { MemoryRecordResponse } from '@/lib/types/api'

const TYPE_LABELS: Record<MemoryRecordResponse['type'], string> = {
  fact: '事实',
  term: '术语',
  decision: '决策',
  risk: '风险',
  preference: '偏好',
  question: '问题',
}

const STATUS_LABELS: Record<MemoryRecordResponse['status'], string> = {
  draft: '待确认',
  accepted: '已接受',
  frozen: '已冻结',
  deprecated: '已过时',
}

interface MemoryCardProps {
  memory: MemoryRecordResponse
  isUpdating?: boolean
  isDeleting?: boolean
  onAccept: (memory: MemoryRecordResponse) => void
  onReview: (memory: MemoryRecordResponse) => void
  onDelete: (memory: MemoryRecordResponse) => void
}

export function MemoryCard({
  memory,
  isUpdating = false,
  isDeleting = false,
  onAccept,
  onReview,
  onDelete,
}: MemoryCardProps) {
  const canAccept = memory.status === 'draft'

  return (
    <Card className="border-border/70">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">{TYPE_LABELS[memory.type]}</Badge>
          <Badge variant={memory.status === 'accepted' ? 'default' : 'secondary'}>
            {STATUS_LABELS[memory.status]}
          </Badge>
          <Badge variant="outline">置信度 {Math.round(memory.confidence * 100)}%</Badge>
          <Badge variant="outline">{memory.scope === 'project' ? '项目' : '用户'}</Badge>
        </div>

        <div className="text-sm leading-6 text-foreground">{memory.text}</div>
      </CardHeader>

      <CardContent className="space-y-3">
        {memory.freshness ? (
          <div className="text-xs text-muted-foreground">freshness: {memory.freshness}</div>
        ) : null}

        <div className="space-y-2">
          <div className="text-xs font-medium text-muted-foreground">来源</div>
          {memory.source_refs.length === 0 ? (
            <div className="rounded-md border border-dashed border-border/70 px-3 py-3 text-xs text-muted-foreground">
              这条记忆当前没有来源引用，不应该进入长期记忆。
            </div>
          ) : (
            <div className="space-y-2">
              {memory.source_refs.slice(0, 3).map((ref) => (
                <div
                  key={`${ref.source_id}:${ref.internal_ref}`}
                  className="rounded-md border border-border/70 px-3 py-3 text-xs leading-5 text-muted-foreground"
                >
                  <div className="font-medium text-foreground">
                    {ref.source_name || ref.source_id}
                    {ref.page_no ? ` · 第 ${ref.page_no} 页` : ''}
                  </div>
                  <div className="mt-1 break-words">
                    {ref.citation_text || ref.internal_ref}
                  </div>
                </div>
              ))}
              {memory.source_refs.length > 3 ? (
                <div className="text-xs text-muted-foreground">
                  还有 {memory.source_refs.length - 3} 条来源引用。
                </div>
              ) : null}
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          onClick={() => onAccept(memory)}
          disabled={!canAccept || isUpdating || isDeleting}
        >
          <Check className="mr-2 h-4 w-4" />
          接受
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => onReview(memory)}
          disabled={isUpdating || isDeleting}
        >
          <Pencil className="mr-2 h-4 w-4" />
          审核 / 编辑
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => onReview(memory)}
          disabled={isUpdating || isDeleting}
        >
          <Archive className="mr-2 h-4 w-4" />
          冻结 / 过时
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => onDelete(memory)}
          disabled={isUpdating || isDeleting}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          删除
        </Button>
      </CardFooter>
    </Card>
  )
}
