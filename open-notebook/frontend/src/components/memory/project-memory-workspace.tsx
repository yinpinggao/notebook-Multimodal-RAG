'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  BrainCircuit,
  Download,
  Pencil,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-react'

import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { DetailSplitLayout, PageHeader } from '@/components/projects/page-templates'
import { MemoryReviewDialog } from '@/components/memory/memory-review-dialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  useDeleteProjectMemory,
  useProjectMemory,
  useRebuildProjectMemory,
  useUpdateProjectMemory,
} from '@/lib/hooks/use-project-memory'
import {
  MemoryRecordResponse,
  MemoryStatus,
  MemoryType,
} from '@/lib/types/api'
import { formatApiError } from '@/lib/utils/error-handler'
import { cn } from '@/lib/utils'

const TYPE_LABELS: Record<MemoryType, string> = {
  fact: '事实',
  term: '术语',
  decision: '决策',
  risk: '风险',
  preference: '偏好',
  question: '问题',
}

const STATUS_LABELS: Record<MemoryStatus, string> = {
  draft: '草稿',
  accepted: '已接受',
  frozen: '已冻结',
  deprecated: '已过时',
}

function MemoryListItem({
  memory,
  isActive,
  onSelect,
}: {
  memory: MemoryRecordResponse
  isActive: boolean
  onSelect: (memoryId: string) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(memory.id)}
      className={cn(
        'w-full rounded-md border p-3 text-left transition-colors',
        isActive
          ? 'border-foreground bg-muted/20'
          : 'border-border/70 bg-background hover:border-foreground/20 hover:bg-muted/20'
      )}
    >
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline">{TYPE_LABELS[memory.type]}</Badge>
        <Badge variant={memory.status === 'accepted' ? 'default' : 'secondary'}>
          {STATUS_LABELS[memory.status]}
        </Badge>
      </div>
      <div className="mt-3 line-clamp-3 text-sm leading-6">{memory.text}</div>
      <div className="mt-3 text-xs text-muted-foreground">
        来源 {memory.source_refs.length} 条 · 置信度 {Math.round(memory.confidence * 100)}%
      </div>
    </button>
  )
}

export function ProjectMemoryWorkspace({ projectId }: { projectId: string }) {
  const {
    data: memories = [],
    isLoading,
    error,
  } = useProjectMemory(projectId)
  const updateProjectMemory = useUpdateProjectMemory(projectId)
  const deleteProjectMemory = useDeleteProjectMemory(projectId)
  const rebuildProjectMemory = useRebuildProjectMemory(projectId)

  const [searchValue, setSearchValue] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | MemoryStatus>('all')
  const [typeFilter, setTypeFilter] = useState<'all' | MemoryType>('all')
  const [activeMemoryId, setActiveMemoryId] = useState<string | null>(null)
  const [reviewingMemory, setReviewingMemory] = useState<MemoryRecordResponse | null>(null)

  const filteredMemories = useMemo(() => {
    const normalizedQuery = searchValue.trim().toLowerCase()

    return memories.filter((memory) => {
      if (statusFilter !== 'all' && memory.status !== statusFilter) {
        return false
      }
      if (typeFilter !== 'all' && memory.type !== typeFilter) {
        return false
      }
      if (!normalizedQuery) {
        return true
      }

      return `${memory.text} ${memory.type} ${memory.status}`
        .toLowerCase()
        .includes(normalizedQuery)
    })
  }, [memories, searchValue, statusFilter, typeFilter])

  useEffect(() => {
    if (!filteredMemories.length) {
      setActiveMemoryId(null)
      return
    }

    if (!activeMemoryId || !filteredMemories.some((memory) => memory.id === activeMemoryId)) {
      setActiveMemoryId(filteredMemories[0].id)
    }
  }, [activeMemoryId, filteredMemories])

  const activeMemory = useMemo(
    () => filteredMemories.find((memory) => memory.id === activeMemoryId) || filteredMemories[0] || null,
    [activeMemoryId, filteredMemories]
  )

  const exportMemories = () => {
    const blob = new Blob([JSON.stringify(memories, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${projectId.replace(/[:/]/g, '_')}-memory.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  const listPane = (
    <div className="space-y-4">
      <div className="grid gap-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchValue}
            onChange={(event) => setSearchValue(event.target.value)}
            placeholder="搜索记忆"
            className="pl-9"
          />
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as 'all' | MemoryStatus)}>
            <SelectTrigger>
              <SelectValue placeholder="全部状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="draft">草稿</SelectItem>
              <SelectItem value="accepted">已接受</SelectItem>
              <SelectItem value="frozen">已冻结</SelectItem>
              <SelectItem value="deprecated">已过时</SelectItem>
            </SelectContent>
          </Select>

          <Select value={typeFilter} onValueChange={(value) => setTypeFilter(value as 'all' | MemoryType)}>
            <SelectTrigger>
              <SelectValue placeholder="全部类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              <SelectItem value="fact">事实</SelectItem>
              <SelectItem value="term">术语</SelectItem>
              <SelectItem value="decision">决策</SelectItem>
              <SelectItem value="risk">风险</SelectItem>
              <SelectItem value="preference">偏好</SelectItem>
              <SelectItem value="question">问题</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-3">
        {isLoading ? (
          <div className="flex min-h-40 items-center justify-center rounded-md border border-dashed border-border/70">
            <LoadingSpinner size="lg" />
          </div>
        ) : filteredMemories.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
            当前没有符合筛选条件的记忆。
          </div>
        ) : (
          filteredMemories.map((memory) => (
            <MemoryListItem
              key={memory.id}
              memory={memory}
              isActive={memory.id === activeMemory?.id}
              onSelect={setActiveMemoryId}
            />
          ))
        )}
      </div>
    </div>
  )

  const detailPane = (
    <div className="space-y-4">
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>记忆列表暂时加载失败</AlertTitle>
          <AlertDescription>{formatApiError(error)}</AlertDescription>
        </Alert>
      ) : null}

      {!activeMemory ? (
        <div className="flex min-h-[24rem] items-center justify-center rounded-md border border-dashed border-border/70 bg-background px-6 text-center text-sm text-muted-foreground">
          先从左侧选择一条记忆，或者先触发一次记忆重建。
        </div>
      ) : (
        <Card className="border-border/70">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">{TYPE_LABELS[activeMemory.type]}</Badge>
                  <Badge variant={activeMemory.status === 'accepted' ? 'default' : 'secondary'}>
                    {STATUS_LABELS[activeMemory.status]}
                  </Badge>
                  <Badge variant="outline">
                    置信度 {Math.round(activeMemory.confidence * 100)}%
                  </Badge>
                </div>
                <CardTitle className="text-xl">记忆详情</CardTitle>
                <CardDescription>
                  先确认内容和来源，再决定接受、冻结、过时或删除。
                </CardDescription>
              </div>

              <div className="flex flex-wrap gap-2">
                {activeMemory.status === 'draft' ? (
                  <Button
                    size="sm"
                    onClick={() =>
                      updateProjectMemory.mutate({
                        memoryId: activeMemory.id,
                        data: { status: 'accepted' },
                      })
                    }
                    disabled={updateProjectMemory.isPending}
                  >
                    接受
                  </Button>
                ) : null}
                <Button size="sm" variant="outline" onClick={() => setReviewingMemory(activeMemory)}>
                  <Pencil className="mr-2 h-4 w-4" />
                  审核 / 编辑
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => deleteProjectMemory.mutate(activeMemory.id)}
                  disabled={deleteProjectMemory.isPending}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  删除
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {updateProjectMemory.error ? (
              <Alert variant="destructive">
                <AlertTitle>更新记忆失败</AlertTitle>
                <AlertDescription>{formatApiError(updateProjectMemory.error)}</AlertDescription>
              </Alert>
            ) : null}

            {deleteProjectMemory.error ? (
              <Alert variant="destructive">
                <AlertTitle>删除记忆失败</AlertTitle>
                <AlertDescription>{formatApiError(deleteProjectMemory.error)}</AlertDescription>
              </Alert>
            ) : null}

            <div className="rounded-md border border-border/70 bg-muted/20 p-4 text-sm leading-7">
              {activeMemory.text}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-md border border-border/70 p-4">
                <div className="text-xs text-muted-foreground">衰减策略</div>
                <div className="mt-2 text-sm">{activeMemory.decay_policy}</div>
              </div>
              <div className="rounded-md border border-border/70 p-4">
                <div className="text-xs text-muted-foreground">freshness</div>
                <div className="mt-2 text-sm">{activeMemory.freshness || '未提供'}</div>
              </div>
            </div>

            <section className="space-y-3">
              <div className="flex items-center gap-2">
                <BrainCircuit className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm font-semibold">来源引用</div>
              </div>

              {activeMemory.source_refs.length === 0 ? (
                <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                  这条记忆当前没有来源引用，不应该进入稳定层。
                </div>
              ) : (
                <div className="space-y-3">
                  {activeMemory.source_refs.map((ref) => (
                    <div
                      key={`${ref.source_id}:${ref.internal_ref}`}
                      className="rounded-md border border-border/70 p-3"
                    >
                      <div className="text-sm font-medium">
                        {ref.source_name || ref.source_id}
                        {ref.page_no ? ` · 第 ${ref.page_no} 页` : ''}
                      </div>
                      <div className="mt-2 text-sm leading-6 text-muted-foreground">
                        {ref.citation_text || ref.internal_ref}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </CardContent>
        </Card>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={<Badge variant="outline">Memory Center</Badge>}
        title="记忆中心"
        description="先把长期记忆过一遍，再决定哪些内容继续沉淀，哪些需要冻结或删除。"
        actions={
          <>
            <Button variant="outline" onClick={exportMemories} disabled={!memories.length}>
              <Download className="mr-2 h-4 w-4" />
              导出
            </Button>
            <Button
              onClick={() => rebuildProjectMemory.mutate()}
              disabled={rebuildProjectMemory.isPending}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              {rebuildProjectMemory.isPending ? '刷新中...' : '刷新记忆'}
            </Button>
          </>
        }
      />

      {rebuildProjectMemory.error ? (
        <Alert variant="destructive">
          <AlertTitle>记忆重建失败</AlertTitle>
          <AlertDescription>{formatApiError(rebuildProjectMemory.error)}</AlertDescription>
        </Alert>
      ) : null}

      <DetailSplitLayout
        rail={listPane}
        detail={detailPane}
        railTitle="记忆列表"
        railDescription="按状态和类型筛选，再进入单条记忆详情。"
        railBadge={<Badge variant="outline">{filteredMemories.length}</Badge>}
      />

      <MemoryReviewDialog
        memory={reviewingMemory}
        open={Boolean(reviewingMemory)}
        isSaving={updateProjectMemory.isPending}
        isDeleting={deleteProjectMemory.isPending}
        onOpenChange={(open) => {
          if (!open) {
            setReviewingMemory(null)
          }
        }}
        onDelete={() => {
          if (!reviewingMemory) {
            return
          }

          deleteProjectMemory.mutate(reviewingMemory.id, {
            onSuccess: () => setReviewingMemory(null),
          })
        }}
        onSave={(payload) => {
          if (!reviewingMemory) {
            return
          }

          updateProjectMemory.mutate(
            {
              memoryId: reviewingMemory.id,
              data: payload,
            },
            {
              onSuccess: () => setReviewingMemory(null),
            }
          )
        }}
      />
    </div>
  )
}
