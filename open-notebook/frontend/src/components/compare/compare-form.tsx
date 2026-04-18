'use client'

import { useEffect, useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ProjectCompareMode, ProjectCompareRequest, SourceListResponse } from '@/lib/types/api'

interface CompareFormProps {
  sources: SourceListResponse[]
  isSubmitting?: boolean
  onSubmit: (request: ProjectCompareRequest) => void
}

const COMPARE_MODE_OPTIONS: Array<{ value: ProjectCompareMode; label: string }> = [
  { value: 'general', label: '综合对比' },
  { value: 'requirements', label: '要求对比' },
  { value: 'risks', label: '风险对比' },
  { value: 'timeline', label: '时间线对比' },
]

export function CompareForm({ sources, isSubmitting = false, onSubmit }: CompareFormProps) {
  const [sourceAId, setSourceAId] = useState('')
  const [sourceBId, setSourceBId] = useState('')
  const [compareMode, setCompareMode] = useState<ProjectCompareMode>('general')

  const sortedSources = useMemo(
    () =>
      [...sources].sort((left, right) =>
        (left.title || left.id).localeCompare(right.title || right.id, 'zh-CN')
      ),
    [sources]
  )

  useEffect(() => {
    if (sortedSources.length < 2) {
      return
    }

    if (!sourceAId) {
      setSourceAId(sortedSources[0].id)
    }

    if (!sourceBId) {
      setSourceBId(sortedSources[1].id)
    }
  }, [sortedSources, sourceAId, sourceBId])

  const sameSourceSelected = !!sourceAId && sourceAId === sourceBId
  const canSubmit = !isSubmitting && !!sourceAId && !!sourceBId && !sameSourceSelected

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle>文档对比</CardTitle>
        <CardDescription>
          先选两份资料，系统会优先复用结构化事实，再回落到摘要线索生成差异结果。
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="compare-source-a">资料 A</Label>
            <Select value={sourceAId} onValueChange={setSourceAId}>
              <SelectTrigger id="compare-source-a">
                <SelectValue placeholder="选择资料 A" />
              </SelectTrigger>
              <SelectContent>
                {sortedSources.map((source) => (
                  <SelectItem key={source.id} value={source.id}>
                    {source.title || source.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="compare-source-b">资料 B</Label>
            <Select value={sourceBId} onValueChange={setSourceBId}>
              <SelectTrigger id="compare-source-b">
                <SelectValue placeholder="选择资料 B" />
              </SelectTrigger>
              <SelectContent>
                {sortedSources.map((source) => (
                  <SelectItem key={source.id} value={source.id}>
                    {source.title || source.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="compare-mode">对比模式</Label>
            <Select
              value={compareMode}
              onValueChange={(value) => setCompareMode(value as ProjectCompareMode)}
            >
              <SelectTrigger id="compare-mode">
                <SelectValue placeholder="选择对比模式" />
              </SelectTrigger>
              <SelectContent>
                {COMPARE_MODE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {sameSourceSelected ? (
          <div className="text-sm text-destructive">请为 A 和 B 选择两份不同的资料。</div>
        ) : null}

        <div className="flex justify-end">
          <Button
            onClick={() =>
              onSubmit({
                source_a_id: sourceAId,
                source_b_id: sourceBId,
                compare_mode: compareMode,
              })
            }
            disabled={!canSubmit}
          >
            {isSubmitting ? '正在创建对比...' : '开始对比'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
