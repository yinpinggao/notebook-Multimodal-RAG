'use client'

import { AlertCircle, FileText, RefreshCw } from 'lucide-react'

import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MarkdownEditor } from '@/components/ui/markdown-editor'
import { ArtifactRecordResponse } from '@/lib/types/api'

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

interface ArtifactEditorProps {
  artifact?: ArtifactRecordResponse | null
  isLoading?: boolean
  isRegenerating?: boolean
  onRegenerate?: (artifactId: string) => void
}

export function ArtifactEditor({
  artifact,
  isLoading = false,
  isRegenerating = false,
  onRegenerate,
}: ArtifactEditorProps) {
  if (isLoading && !artifact) {
    return (
      <div className="flex min-h-[36rem] items-center justify-center rounded-md border border-border/70 bg-background">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!artifact) {
    return (
      <div className="flex min-h-[36rem] items-center justify-center rounded-md border border-dashed border-border/70 bg-background px-6 text-center text-sm text-muted-foreground">
        先从左侧选择一个产物，或直接生成一个新的输出。
      </div>
    )
  }

  const isPending = artifact.status === 'queued' || artifact.status === 'running'

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-border/70 bg-background">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border/70 px-6 py-5">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <div className="text-base font-semibold">{artifact.title}</div>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Badge variant={artifact.status === 'ready' ? 'default' : 'outline'}>
                {STATUS_LABELS[artifact.status]}
              </Badge>
              <span>{ARTIFACT_TYPE_LABELS[artifact.artifact_type]}</span>
              <span>生成任务 {artifact.created_by_run_id}</span>
              <span>来源引用 {artifact.source_refs.length} 条</span>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            disabled={isRegenerating}
            onClick={() => onRegenerate?.(artifact.id)}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {isRegenerating ? '重生成中...' : '重新生成'}
          </Button>
        </div>

        <div className="space-y-4 px-6 py-5">
          {artifact.error_message ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>本次生成失败</AlertTitle>
              <AlertDescription>{artifact.error_message}</AlertDescription>
            </Alert>
          ) : null}

          {isPending ? (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>产物仍在生成</AlertTitle>
              <AlertDescription>页面会自动刷新，生成完成后这里会直接显示 markdown 内容。</AlertDescription>
            </Alert>
          ) : null}

          {artifact.content_md ? (
            <MarkdownEditor
              value={artifact.content_md}
              preview="preview"
              hideToolbar
              height={560}
              className="[&_pre]:whitespace-pre-wrap"
            />
          ) : (
            <div className="rounded-md border border-dashed border-border/70 px-4 py-8 text-sm text-muted-foreground">
              {isPending ? '正在准备内容...' : '当前产物还没有可展示的 markdown 内容。'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
