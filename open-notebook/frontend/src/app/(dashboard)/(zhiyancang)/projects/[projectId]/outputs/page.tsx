'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { faArrowRotateRight, faFileCirclePlus, faSpinner } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { MobileDrawer } from '@/components/zhiyancang/layout/mobile-drawer'
import { OutputTemplateSelector } from '@/components/zhiyancang/outputs/output-template-selector'
import { OutputsWaterfall } from '@/components/zhiyancang/outputs/outputs-waterfall'
import { VersionHistorySidebar } from '@/components/zhiyancang/outputs/version-history-sidebar'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  useCreateProjectArtifact,
  useProjectArtifact,
  useRegenerateProjectArtifact,
} from '@/lib/hooks/use-project-artifacts'
import { useMediaQuery } from '@/lib/hooks/use-media-query'
import { useZycProjectDetail } from '@/lib/hooks/use-zyc-project-detail'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import { formatApiError } from '@/lib/utils/error-handler'

const TEMPLATE_TO_ARTIFACT = {
  'Project Summary': { artifact_type: 'project_summary', title: undefined },
  'Defense Pitch': { artifact_type: 'defense_outline', title: undefined },
  'Poster Copy': { artifact_type: 'project_summary', title: 'Poster Copy' },
  'PPT Outline': { artifact_type: 'defense_outline', title: 'PPT Outline' },
  'Competition Brief': { artifact_type: 'diff_report', title: 'Competition Brief' },
} as const

type OriginKind = 'overview' | 'compare' | 'thread'

export default function ProjectOutputsPage() {
  const params = useParams()
  const projectId = String(params?.projectId || '')
  const { data, error, isLoading, meta } = useZycProjectDetail(projectId)
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const isMobile = useMediaQuery('(max-width: 639px)')
  const createArtifact = useCreateProjectArtifact(projectId)
  const regenerateArtifact = useRegenerateProjectArtifact(projectId)
  const {
    outputHistoryOpen,
    selectedOutputTemplate,
    setOutputHistoryOpen,
    setSelectedOutputTemplate,
    selectedOutputVersionId,
    setSelectedOutputVersionId,
  } = useZycUIStore()
  const [originKind, setOriginKind] = useState<OriginKind>('overview')

  const selectedItem = useMemo(() => {
    if (!data) {
      return null
    }

    return (
      data.outputs.find((item) => item.template === selectedOutputTemplate) ??
      data.outputs[0] ??
      null
    )
  }, [data, selectedOutputTemplate])

  const resolvedVersionId =
    selectedItem?.versions.some((version) => version.id === selectedOutputVersionId)
      ? selectedOutputVersionId
      : selectedItem?.versions[0]?.id
  const versionArtifactQuery = useProjectArtifact(projectId, resolvedVersionId || undefined)

  const templateOptions = useMemo(() => {
    const defaults = Object.keys(TEMPLATE_TO_ARTIFACT)
    if (!data) {
      return defaults
    }

    return [...new Set([...defaults, ...data.outputs.map((item) => item.template)])]
  }, [data])

  const originOptions = useMemo(() => {
    const options: Array<{ id: OriginKind; label: string; value?: string }> = [
      { id: 'overview', label: 'Overview' },
    ]

    if (meta.compares[0]?.id) {
      options.push({ id: 'compare', label: 'Latest Compare', value: meta.compares[0].id })
    }

    if (meta.activeThreadId) {
      options.push({ id: 'thread', label: 'Active Thread', value: meta.activeThreadId })
    }

    return options
  }, [meta.activeThreadId, meta.compares])

  useEffect(() => {
    if (!templateOptions.includes(selectedOutputTemplate)) {
      setSelectedOutputTemplate(templateOptions[0] || 'Project Summary')
    }
  }, [selectedOutputTemplate, setSelectedOutputTemplate, templateOptions])

  useEffect(() => {
    if (!selectedItem) {
      return
    }
    if (selectedItem.versions[0]?.id) {
      setSelectedOutputVersionId(selectedItem.versions[0].id)
    }
  }, [selectedItem, setSelectedOutputVersionId])

  useEffect(() => {
    if (!originOptions.some((option) => option.id === originKind)) {
      setOriginKind(originOptions[0]?.id || 'overview')
    }
  }, [originKind, originOptions])

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Outputs unavailable</AlertTitle>
        <AlertDescription>{formatApiError(error)}</AlertDescription>
      </Alert>
    )
  }

  if (isLoading || !data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  const history = (
    <VersionHistorySidebar
      item={selectedItem}
      isRegenerating={regenerateArtifact.isPending}
      onRegenerate={(artifactId) => {
        void regenerateArtifact.mutateAsync(artifactId)
      }}
    />
  )

  const selectedOrigin = originOptions.find((option) => option.id === originKind)
  const canGenerate = originKind === 'overview' || Boolean(selectedOrigin?.value)

  const handleCreateArtifact = async () => {
    const template = TEMPLATE_TO_ARTIFACT[
      (selectedOutputTemplate in TEMPLATE_TO_ARTIFACT
        ? selectedOutputTemplate
        : 'Project Summary') as keyof typeof TEMPLATE_TO_ARTIFACT
    ]

    try {
      await createArtifact.mutateAsync({
        artifact_type: template.artifact_type,
        origin_kind: originKind,
        origin_id: selectedOrigin?.value,
        title: template.title,
      })
    } catch {
      // Inline error state handles this.
    }
  }

  return (
    <div className="space-y-4">
      <OutputTemplateSelector templates={templateOptions} />

      <div className="zyc-glass rounded-[24px] px-5 py-5">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_220px_220px_auto]">
          <div className="text-sm leading-7 text-white/60">
            Generate artifacts from the live overview, the latest compare, or the active evidence
            thread. Version history stays attached to the current template.
          </div>
          <Select value={originKind} onValueChange={(value) => setOriginKind(value as OriginKind)}>
            <SelectTrigger className="h-12 rounded-[20px] border-white/10 bg-white/6 text-white">
              <SelectValue placeholder="Choose origin" />
            </SelectTrigger>
            <SelectContent className="rounded-[20px] border-white/10 bg-[#18191d]/96 text-white">
              {originOptions.map((option) => (
                <SelectItem key={option.id} value={option.id}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="rounded-[20px] border border-white/8 bg-white/4 px-4 py-3 text-sm text-white/56">
            {selectedOutputTemplate}
          </div>
            <Button
              type="button"
              onClick={() => {
                void handleCreateArtifact()
              }}
              disabled={createArtifact.isPending || !canGenerate}
              className="rounded-full bg-white text-zinc-950 hover:bg-white/92"
            >
            {createArtifact.isPending ? (
              <FontAwesomeIcon icon={faSpinner} className="mr-2 animate-spin" />
            ) : (
              <FontAwesomeIcon icon={faFileCirclePlus} className="mr-2" />
            )}
            Generate
          </Button>
        </div>

        {createArtifact.error || regenerateArtifact.error || versionArtifactQuery.error ? (
          <Alert variant="destructive" className="mt-4">
            <AlertTitle>Output action failed</AlertTitle>
            <AlertDescription>
              {formatApiError(
                createArtifact.error || regenerateArtifact.error || versionArtifactQuery.error
              )}
            </AlertDescription>
          </Alert>
        ) : null}
      </div>

      {isDesktop ? (
        <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)_320px]">
          <div className="rounded-[24px] border border-white/8 bg-white/4 px-5 py-5 text-sm leading-7 text-white/62">
            {versionArtifactQuery.data?.content_md
              ? versionArtifactQuery.data.content_md.slice(0, 240)
              : 'Pick a template, generate from a live origin, then reopen a version from the sidebar.'}
          </div>
          <OutputsWaterfall items={data.outputs} />
          {history}
        </div>
      ) : (
        <>
          <div className="flex justify-end">
            <Button
              onClick={() => setOutputHistoryOpen(true)}
              className="rounded-full bg-white text-zinc-950 hover:bg-white/92"
            >
              <FontAwesomeIcon icon={faArrowRotateRight} className="mr-2" />
              Version History
            </Button>
          </div>
          <OutputsWaterfall items={data.outputs} />
          <MobileDrawer
            open={outputHistoryOpen}
            onOpenChange={setOutputHistoryOpen}
            side={isMobile ? 'bottom' : 'right'}
            title="Version History"
            description="Switch, inspect, and regenerate output versions."
          >
            {history}
          </MobileDrawer>
        </>
      )}
    </div>
  )
}
