'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { faDownload, faScaleBalanced, faSpinner } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { CompareResultGrid } from '@/components/zhiyancang/compare/compare-result-grid'
import { CompareSourceSelector } from '@/components/zhiyancang/compare/compare-source-selector'
import { CompareStatusBar } from '@/components/zhiyancang/compare/compare-status-bar'
import {
  useCreateProjectCompare,
  useExportProjectCompare,
} from '@/lib/hooks/use-project-compare'
import { useZycProjectDetail } from '@/lib/hooks/use-zyc-project-detail'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import { formatApiError } from '@/lib/utils/error-handler'

export default function ProjectComparePage() {
  const params = useParams()
  const projectId = String(params?.projectId || '')
  const { data, error, isLoading, meta } = useZycProjectDetail(projectId)
  const {
    selectedCompareSourceA,
    selectedCompareSourceB,
    setSelectedCompareSourceA,
    setSelectedCompareSourceB,
  } = useZycUIStore()
  const createCompare = useCreateProjectCompare(projectId)
  const exportCompare = useExportProjectCompare(projectId)
  const [markdownPreview, setMarkdownPreview] = useState('')

  useEffect(() => {
    if (!data?.compare.sources.length) {
      return
    }

    const sourceA = data.compare.sources[0]?.id || ''
    const sourceB = data.compare.sources[1]?.id || data.compare.sources[0]?.id || ''

    const hasSourceA = data.compare.sources.some((source) => source.id === selectedCompareSourceA)
    const hasSourceB = data.compare.sources.some((source) => source.id === selectedCompareSourceB)

    if (!selectedCompareSourceA || !hasSourceA) {
      setSelectedCompareSourceA(sourceA)
    }

    if (!selectedCompareSourceB || !hasSourceB) {
      setSelectedCompareSourceB(sourceB)
    }
  }, [
    data?.compare.sources,
    selectedCompareSourceA,
    selectedCompareSourceB,
    setSelectedCompareSourceA,
    setSelectedCompareSourceB,
  ])

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Compare unavailable</AlertTitle>
        <AlertDescription>{formatApiError(error)}</AlertDescription>
      </Alert>
    )
  }

  if (isLoading || !data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <FontAwesomeIcon icon={faSpinner} className="animate-spin text-2xl text-white/60" />
      </div>
    )
  }

  const activeCompare = meta.compares[0]

  const handleRunCompare = async () => {
    if (!selectedCompareSourceA || !selectedCompareSourceB) {
      return
    }

    try {
      setMarkdownPreview('')
      await createCompare.mutateAsync({
        source_a_id: selectedCompareSourceA,
        source_b_id: selectedCompareSourceB,
      })
    } catch {
      // Inline error state handles this.
    }
  }

  const handleExport = async () => {
    if (!activeCompare?.id) {
      return
    }

    try {
      const response = await exportCompare.mutateAsync(activeCompare.id)
      setMarkdownPreview(response.content)

      const blob = new Blob([response.content], {
        type: 'text/markdown;charset=utf-8',
      })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${activeCompare.id}.md`
      anchor.click()
      URL.revokeObjectURL(url)
    } catch {
      // Inline error state handles this.
    }
  }

  return (
    <div className="space-y-4">
      <div className="zyc-glass rounded-[24px] px-5 py-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-medium text-white">Dual Source Selector</div>
            <p className="mt-1 text-sm leading-6 text-white/58">
              Compare runs on live project sources. The latest compare result stays pinned below.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              onClick={() => {
                void handleRunCompare()
              }}
              disabled={
                createCompare.isPending ||
                !selectedCompareSourceA ||
                !selectedCompareSourceB ||
                selectedCompareSourceA === selectedCompareSourceB
              }
              className="rounded-full bg-white text-zinc-950 hover:bg-white/92"
            >
              {createCompare.isPending ? (
                <FontAwesomeIcon icon={faSpinner} className="mr-2 animate-spin" />
              ) : (
                <FontAwesomeIcon icon={faScaleBalanced} className="mr-2" />
              )}
              Run Compare
            </Button>

            <Button
              type="button"
              variant="outline"
              onClick={() => {
                void handleExport()
              }}
              disabled={!activeCompare?.id || exportCompare.isPending}
              className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
            >
              <FontAwesomeIcon icon={faDownload} className="mr-2" />
              Export Markdown
            </Button>
          </div>
        </div>

        <div className="mt-4">
          <CompareSourceSelector compare={data.compare} />
        </div>

        {createCompare.error ? (
          <Alert variant="destructive" className="mt-4">
            <AlertTitle>Compare failed</AlertTitle>
            <AlertDescription>{formatApiError(createCompare.error)}</AlertDescription>
          </Alert>
        ) : null}
      </div>

      <CompareStatusBar status={data.compare.status} />
      <CompareResultGrid compare={data.compare} />

      <div className="rounded-[24px] border border-white/8 bg-white/4 px-5 py-5">
        <div className="text-sm font-medium text-white">Latest Compare Summary</div>
        <div className="mt-3 text-sm leading-7 text-white/66">
          {activeCompare?.result?.summary ||
            'No compare result yet. Pick two sources and run a compare to surface similarities, differences, conflicts, and missing items.'}
        </div>

        {exportCompare.error ? (
          <Alert variant="destructive" className="mt-4">
            <AlertTitle>Export failed</AlertTitle>
            <AlertDescription>{formatApiError(exportCompare.error)}</AlertDescription>
          </Alert>
        ) : null}

        <div className="mt-4 rounded-[20px] border border-white/8 bg-black/18 px-4 py-4">
          {markdownPreview ? (
            <pre className="overflow-x-auto whitespace-pre-wrap text-xs leading-6 text-white/68">
              {markdownPreview}
            </pre>
          ) : (
            <div className="text-sm text-white/46">
              Exported markdown preview will appear here.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
