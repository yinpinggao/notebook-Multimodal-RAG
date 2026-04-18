'use client'

import { FileText, RefreshCw } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { formatProjectTimestamp } from '@/lib/project-workspace'
import { ArtifactRecordResponse } from '@/lib/types/api'
import { cn } from '@/lib/utils'

const ARTIFACT_TYPE_LABELS: Record<ArtifactRecordResponse['artifact_type'], string> = {
  project_summary: '项目综述',
  literature_review: '文献综述',
  diff_report: '差异报告',
  risk_list: '风险清单',
  defense_outline: '答辩提纲',
  judge_questions: '评委问题清单',
  qa_cards: '问答卡片',
  presentation_script: '汇报讲稿',
  podcast: '播客',
}

const STATUS_LABELS: Record<ArtifactRecordResponse['status'], string> = {
  queued: '排队中',
  running: '生成中',
  draft: '草稿',
  ready: '已完成',
  archived: '已归档',
  failed: '失败',
}

interface ArtifactListProps {
  artifacts: ArtifactRecordResponse[]
  activeArtifactId?: string | null
  isLoading?: boolean
  onSelect: (artifactId: string) => void
  onRegenerate: (artifactId: string) => void
  isRegenerating?: boolean
}

export function ArtifactList({
  artifacts,
  activeArtifactId,
  isLoading = false,
  onSelect,
  onRegenerate,
  isRegenerating = false,
}: ArtifactListProps) {
  return (
    <div className="rounded-md border border-border/70 bg-background">
      <div className="border-b border-border/70 px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">已有产物</div>
            <div className="mt-1 text-xs text-muted-foreground">
              先看完成的内容，也可以对任一产物重新生成。
            </div>
          </div>
          <Badge variant="outline">{artifacts.length}</Badge>
        </div>
      </div>

      <ScrollArea className="h-[28rem]">
        <div className="space-y-3 px-4 py-4">
          {isLoading ? (
            <div className="rounded-md border border-dashed border-border/70 px-4 py-8 text-sm text-muted-foreground">
              正在加载产物列表...
            </div>
          ) : artifacts.length === 0 ? (
            <div className="rounded-md border border-dashed border-border/70 px-4 py-8 text-sm text-muted-foreground">
              还没有产物。先从综述、差异报告或问答卡片开始。
            </div>
          ) : (
            artifacts.map((artifact) => {
              const isActive = artifact.id === activeArtifactId

              return (
                <div
                  key={artifact.id}
                  className={cn(
                    'rounded-md border px-3 py-3',
                    isActive ? 'border-primary bg-primary/5' : 'border-border/70'
                  )}
                >
                  <button
                    type="button"
                    className="w-full text-left"
                    onClick={() => onSelect(artifact.id)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 text-sm font-medium">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          <span className="break-words">{artifact.title}</span>
                        </div>
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                          <Badge variant={artifact.status === 'ready' ? 'default' : 'outline'}>
                            {STATUS_LABELS[artifact.status]}
                          </Badge>
                          <span>{ARTIFACT_TYPE_LABELS[artifact.artifact_type]}</span>
                          <span>{formatProjectTimestamp(artifact.updated_at)}</span>
                        </div>
                      </div>
                    </div>
                  </button>

                  <div className="mt-3 flex items-center justify-between gap-3">
                    <div className="text-xs text-muted-foreground">
                      {artifact.origin_kind === 'compare'
                        ? '来源：对比结果'
                        : artifact.origin_kind === 'thread'
                          ? '来源：问答线程'
                          : '来源：项目总览'}
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={isRegenerating}
                      onClick={() => onRegenerate(artifact.id)}
                    >
                      <RefreshCw className="mr-1 h-3.5 w-3.5" />
                      重生成
                    </Button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
