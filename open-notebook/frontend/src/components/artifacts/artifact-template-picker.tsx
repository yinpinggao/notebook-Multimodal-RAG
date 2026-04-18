'use client'

import { useEffect, useMemo, useState } from 'react'
import { FileStack, ListChecks, MessageSquareQuote, ShieldQuestion } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  ArtifactOriginKind,
  ProjectArtifactRequest,
} from '@/lib/types/api'

const ARTIFACT_TYPES_BY_ORIGIN: Record<ArtifactOriginKind, ProjectArtifactRequest['artifact_type'][]> = {
  overview: ['project_summary', 'defense_outline', 'judge_questions'],
  compare: ['diff_report', 'defense_outline', 'judge_questions'],
  thread: ['qa_cards', 'defense_outline', 'judge_questions'],
}

const ARTIFACT_TYPE_LABELS: Record<ProjectArtifactRequest['artifact_type'], string> = {
  project_summary: '项目综述',
  diff_report: '差异报告',
  defense_outline: '答辩提纲',
  judge_questions: '评委问题清单',
  qa_cards: '问答卡片',
}

interface ArtifactSourceOption {
  id: string
  label: string
}

interface ArtifactTemplatePickerProps {
  projectName?: string
  threadOptions: ArtifactSourceOption[]
  compareOptions: ArtifactSourceOption[]
  onCreate: (request: ProjectArtifactRequest) => void
  isSubmitting?: boolean
}

export function ArtifactTemplatePicker({
  projectName,
  threadOptions,
  compareOptions,
  onCreate,
  isSubmitting = false,
}: ArtifactTemplatePickerProps) {
  const [originKind, setOriginKind] = useState<ArtifactOriginKind>('overview')
  const [artifactType, setArtifactType] = useState<ProjectArtifactRequest['artifact_type']>('project_summary')
  const [originId, setOriginId] = useState('')
  const [title, setTitle] = useState('')

  const allowedTypes = useMemo(
    () => ARTIFACT_TYPES_BY_ORIGIN[originKind],
    [originKind]
  )
  const currentSourceOptions = originKind === 'thread' ? threadOptions : compareOptions

  useEffect(() => {
    if (!allowedTypes.includes(artifactType)) {
      setArtifactType(allowedTypes[0])
    }
  }, [allowedTypes, artifactType])

  useEffect(() => {
    if (originKind === 'overview') {
      setOriginId('')
      return
    }

    setOriginId((current) => {
      if (current && currentSourceOptions.some((option) => option.id === current)) {
        return current
      }
      return currentSourceOptions[0]?.id || ''
    })
  }, [currentSourceOptions, originKind])

  const submitManualRequest = () => {
    const request: ProjectArtifactRequest = {
      artifact_type: artifactType,
      origin_kind: originKind,
    }

    if (originKind !== 'overview' && originId) {
      request.origin_id = originId
    }

    if (title.trim()) {
      request.title = title.trim()
    }

    onCreate(request)
  }

  return (
    <div className="rounded-md border border-border/70 bg-background">
      <div className="border-b border-border/70 px-4 py-4">
        <div className="text-sm font-semibold">产物模版</div>
        <div className="mt-1 text-xs leading-5 text-muted-foreground">
          先把问答、总览和对比结果沉淀成 markdown 产物，后续再接导出。
        </div>
      </div>

      <div className="space-y-5 px-4 py-4">
        <div className="space-y-3">
          <div className="text-xs font-medium text-muted-foreground">一键生成</div>

          <div className="grid gap-2">
            <Button
              type="button"
              variant="outline"
              className="justify-start"
              disabled={isSubmitting}
              onClick={() => onCreate({ artifact_type: 'project_summary', origin_kind: 'overview' })}
            >
              <FileStack className="mr-2 h-4 w-4" />
              从项目总览生成项目综述
            </Button>

            <Button
              type="button"
              variant="outline"
              className="justify-start"
              disabled={isSubmitting || threadOptions.length === 0}
              onClick={() =>
                onCreate({
                  artifact_type: 'qa_cards',
                  origin_kind: 'thread',
                  origin_id: threadOptions[0]?.id,
                })
              }
            >
              <MessageSquareQuote className="mr-2 h-4 w-4" />
              从最新问答生成问答卡片
            </Button>

            <Button
              type="button"
              variant="outline"
              className="justify-start"
              disabled={isSubmitting || compareOptions.length === 0}
              onClick={() =>
                onCreate({
                  artifact_type: 'diff_report',
                  origin_kind: 'compare',
                  origin_id: compareOptions[0]?.id,
                })
              }
            >
              <ListChecks className="mr-2 h-4 w-4" />
              从最新对比生成差异报告
            </Button>
          </div>
        </div>

        <div className="space-y-3 border-t border-border/70 pt-5">
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <ShieldQuestion className="h-3.5 w-3.5" />
            手动生成
          </div>

          <div className="space-y-2">
            <Label htmlFor="artifact-origin-kind">来源</Label>
            <Select value={originKind} onValueChange={(value) => setOriginKind(value as ArtifactOriginKind)}>
              <SelectTrigger id="artifact-origin-kind" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="overview">项目总览</SelectItem>
                <SelectItem value="thread">问答线程</SelectItem>
                <SelectItem value="compare">对比结果</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="artifact-type">产物类型</Label>
            <Select
              value={artifactType}
              onValueChange={(value) => setArtifactType(value as ProjectArtifactRequest['artifact_type'])}
            >
              <SelectTrigger id="artifact-type" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {allowedTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {ARTIFACT_TYPE_LABELS[type]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {originKind !== 'overview' ? (
            <div className="space-y-2">
              <Label htmlFor="artifact-origin-id">来源对象</Label>
              <Select value={originId} onValueChange={setOriginId}>
                <SelectTrigger id="artifact-origin-id" className="w-full">
                  <SelectValue placeholder={originKind === 'thread' ? '选择线程' : '选择对比结果'} />
                </SelectTrigger>
                <SelectContent>
                  {currentSourceOptions.length === 0 ? (
                    <SelectItem value="__empty" disabled>
                      暂无可用来源
                    </SelectItem>
                  ) : (
                    currentSourceOptions.map((option) => (
                      <SelectItem key={option.id} value={option.id}>
                        {option.label}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
          ) : null}

          <div className="space-y-2">
            <Label htmlFor="artifact-title">自定义标题</Label>
            <Input
              id="artifact-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder={projectName ? `${projectName} ${ARTIFACT_TYPE_LABELS[artifactType]}` : '留空时使用默认标题'}
            />
          </div>

          <Button
            type="button"
            className="w-full"
            disabled={isSubmitting || (originKind !== 'overview' && !originId)}
            onClick={submitManualRequest}
          >
            {isSubmitting ? '生成中...' : '生成产物'}
          </Button>
        </div>
      </div>
    </div>
  )
}
