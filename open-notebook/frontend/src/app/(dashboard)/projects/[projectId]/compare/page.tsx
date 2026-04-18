'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { AlertCircle, Download, GitCompareArrows } from 'lucide-react'

import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { CompareForm } from '@/components/compare/compare-form'
import { CompareSummary } from '@/components/compare/compare-summary'
import { ConflictList } from '@/components/compare/conflict-list'
import { DiffTable } from '@/components/compare/diff-table'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  useCreateProjectCompare,
  useExportProjectCompare,
  useProjectCompare,
  useProjectCompares,
} from '@/lib/hooks/use-project-compare'
import { useNotebookSources } from '@/lib/hooks/use-sources'
import { projectIdToNotebookId } from '@/lib/project-alias'
import { ProjectCompareRequest } from '@/lib/types/api'
import { formatApiError } from '@/lib/utils/error-handler'

export default function ProjectComparePage() {
  const params = useParams()
  const routeProjectId = params?.projectId ? String(params.projectId) : ''
  const projectId = projectIdToNotebookId(routeProjectId)

  const [activeCompareId, setActiveCompareId] = useState<string | null>(null)
  const [markdownPreview, setMarkdownPreview] = useState<string>('')

  const {
    sources,
    isLoading: sourcesLoading,
    error: sourcesError,
  } = useNotebookSources(projectId)
  const {
    data: compares = [],
    error: comparesError,
  } = useProjectCompares(projectId)
  const createCompare = useCreateProjectCompare(projectId)
  const exportCompare = useExportProjectCompare(projectId)
  const {
    data: compare,
    isLoading: compareLoading,
    error: compareError,
  } = useProjectCompare(projectId, activeCompareId || undefined)

  useEffect(() => {
    if (!activeCompareId && compares.length > 0) {
      setActiveCompareId(compares[0].id)
    }
  }, [activeCompareId, compares])

  const handleCreateCompare = async (request: ProjectCompareRequest) => {
    setMarkdownPreview('')
    try {
      const response = await createCompare.mutateAsync(request)
      setActiveCompareId(response.compare_id)
    } catch {}
  }

  const handleExportMarkdown = async () => {
    if (!compare?.id) {
      return
    }

    try {
      const response = await exportCompare.mutateAsync(compare.id)
      setMarkdownPreview(response.content)

      const blob = new Blob([response.content], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${compare.id}.md`
      anchor.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  if (sourcesError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>对比页暂时加载失败</AlertTitle>
        <AlertDescription>{formatApiError(sourcesError)}</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      <Card className="border-border/70">
        <CardHeader>
          <div className="flex items-center gap-2">
            <GitCompareArrows className="h-4 w-4 text-muted-foreground" />
            <CardTitle>对比中心</CardTitle>
          </div>
          <CardDescription>
            先从两份资料的结构化事实开始对齐，再把差异、冲突、缺失点沉淀成可复看的结果。
          </CardDescription>
        </CardHeader>
      </Card>

      {comparesError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>已有对比列表加载失败</AlertTitle>
          <AlertDescription>{formatApiError(comparesError)}</AlertDescription>
        </Alert>
      ) : null}

      {compares.length > 0 ? (
        <Card className="border-border/70">
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle>已有对比</CardTitle>
                <CardDescription>
                  Demo 预置结果和历史对比会优先出现在这里，进入页面后会自动打开最近一条。
                </CardDescription>
              </div>
              <Badge variant="outline">{compares.length} 条</Badge>
            </div>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {compares.map((item) => (
              <Button
                key={item.id}
                type="button"
                variant={item.id === activeCompareId ? 'default' : 'outline'}
                size="sm"
                className="max-w-full justify-start"
                onClick={() => {
                  setMarkdownPreview('')
                  setActiveCompareId(item.id)
                }}
              >
                <span className="truncate">
                  {item.source_a_title} / {item.source_b_title}
                </span>
                <span className="text-xs opacity-80">{item.status}</span>
              </Button>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {sourcesLoading ? (
        <div className="flex min-h-[20rem] items-center justify-center rounded-lg border border-dashed border-border/70">
          <LoadingSpinner size="lg" />
        </div>
      ) : sources.length < 2 ? (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>资料还不够</AlertTitle>
          <AlertDescription>至少需要两份项目资料，才能开始文档对比。</AlertDescription>
        </Alert>
      ) : (
        <CompareForm
          sources={sources}
          isSubmitting={createCompare.isPending}
          onSubmit={(request) => {
            void handleCreateCompare(request)
          }}
        />
      )}

      {createCompare.error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>创建对比失败</AlertTitle>
          <AlertDescription>{formatApiError(createCompare.error)}</AlertDescription>
        </Alert>
      ) : null}

      {compareError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>对比结果加载失败</AlertTitle>
          <AlertDescription>{formatApiError(compareError)}</AlertDescription>
        </Alert>
      ) : null}

      {compareLoading && activeCompareId ? (
        <Card className="border-border/70">
          <CardContent className="flex min-h-40 items-center justify-center">
            <LoadingSpinner size="lg" />
          </CardContent>
        </Card>
      ) : null}

      {compare ? (
        <>
          <CompareSummary compare={compare} />

          {(compare.status === 'queued' || compare.status === 'running') && !compare.result ? (
            <Card className="border-border/70">
              <CardContent className="flex items-center gap-3 py-6 text-sm text-muted-foreground">
                <LoadingSpinner size="sm" />
                正在生成对比结果，页面会自动刷新。
              </CardContent>
            </Card>
          ) : null}

          {compare.result ? (
            <>
              <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
                <DiffTable compare={compare} />
                <ConflictList compare={compare} />
              </div>

              <Card className="border-border/70">
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <CardTitle>导出报告</CardTitle>
                      <CardDescription>先导出 markdown，既能下载，也能在页内直接复看。</CardDescription>
                    </div>
                    <Button
                      onClick={() => {
                        void handleExportMarkdown()
                      }}
                      disabled={exportCompare.isPending}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      {exportCompare.isPending ? '导出中...' : '导出 Markdown'}
                    </Button>
                  </div>
                </CardHeader>

                <CardContent>
                  {exportCompare.error ? (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertTitle>导出失败</AlertTitle>
                      <AlertDescription>{formatApiError(exportCompare.error)}</AlertDescription>
                    </Alert>
                  ) : markdownPreview ? (
                    <pre className="overflow-x-auto rounded-md border border-border/70 bg-muted/30 p-4 text-xs leading-6">
                      {markdownPreview}
                    </pre>
                  ) : (
                    <div className="rounded-md border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                      导出后，markdown 预览会显示在这里。
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
