'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { AlertCircle } from 'lucide-react'

import { ArtifactEditor } from '@/components/artifacts/artifact-editor'
import { ArtifactList } from '@/components/artifacts/artifact-list'
import { ArtifactTemplatePicker } from '@/components/artifacts/artifact-template-picker'
import { DetailSplitLayout, PageHeader } from '@/components/projects/page-templates'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  useCreateProjectArtifact,
  useProjectArtifact,
  useProjectArtifacts,
  useRegenerateProjectArtifact,
} from '@/lib/hooks/use-project-artifacts'
import { useProjectCompares } from '@/lib/hooks/use-project-compare'
import { useProjectThreads } from '@/lib/hooks/use-project-evidence'
import { useProjectOverview } from '@/lib/hooks/use-projects'
import { projectIdToNotebookId } from '@/lib/project-alias'
import { ProjectArtifactRequest } from '@/lib/types/api'
import { formatApiError } from '@/lib/utils/error-handler'

export default function ProjectOutputsPage() {
  const params = useParams()
  const routeProjectId = params?.projectId ? String(params.projectId) : ''
  const projectId = projectIdToNotebookId(routeProjectId)

  const [activeArtifactId, setActiveArtifactId] = useState<string | null>(null)

  const { data: overview, error: overviewError } = useProjectOverview(projectId)
  const {
    data: artifacts = [],
    isLoading: artifactsLoading,
    error: artifactsError,
  } = useProjectArtifacts(projectId)
  const {
    data: activeArtifact,
    isLoading: activeArtifactLoading,
  } = useProjectArtifact(projectId, activeArtifactId || undefined)
  const { data: threads = [], error: threadsError } = useProjectThreads(projectId)
  const { data: compares = [], error: comparesError } = useProjectCompares(projectId)

  const createArtifact = useCreateProjectArtifact(projectId)
  const regenerateArtifact = useRegenerateProjectArtifact(projectId)

  useEffect(() => {
    if (!artifacts.length) {
      setActiveArtifactId(null)
      return
    }

    if (!activeArtifactId || !artifacts.some((artifact) => artifact.id === activeArtifactId)) {
      setActiveArtifactId(artifacts[0].id)
    }
  }, [activeArtifactId, artifacts])

  const selectedArtifact = activeArtifact ?? artifacts.find((artifact) => artifact.id === activeArtifactId) ?? null

  const completedCompares = useMemo(
    () => compares.filter((compare) => compare.status === 'completed'),
    [compares]
  )
  const threadOptions = useMemo(
    () => threads.map((thread) => ({ id: thread.id, label: thread.title })),
    [threads]
  )
  const compareOptions = useMemo(
    () =>
      completedCompares.map((compare) => ({
        id: compare.id,
        label: `${compare.source_a_title} vs ${compare.source_b_title}`,
      })),
    [completedCompares]
  )

  const handleCreateArtifact = async (request: ProjectArtifactRequest) => {
    try {
      const response = await createArtifact.mutateAsync(request)
      setActiveArtifactId(response.artifact_id)
    } catch {
      // Errors are rendered inline.
    }
  }

  const handleRegenerateArtifact = async (artifactId: string) => {
    try {
      const response = await regenerateArtifact.mutateAsync(artifactId)
      setActiveArtifactId(response.artifact_id)
    } catch {
      // Errors are rendered inline.
    }
  }

  const topLevelError = artifactsError || threadsError || comparesError || overviewError

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={<Badge variant="outline">Output Studio</Badge>}
        title="输出工坊"
        description="把问答、项目总览和资料对比沉淀成可交付的 markdown 产物。"
      />

      {topLevelError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>输出页暂时加载失败</AlertTitle>
          <AlertDescription>{formatApiError(topLevelError)}</AlertDescription>
        </Alert>
      ) : null}

      {createArtifact.error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>创建产物失败</AlertTitle>
          <AlertDescription>{formatApiError(createArtifact.error)}</AlertDescription>
        </Alert>
      ) : null}

      {regenerateArtifact.error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>重生成失败</AlertTitle>
          <AlertDescription>{formatApiError(regenerateArtifact.error)}</AlertDescription>
        </Alert>
      ) : null}

      <DetailSplitLayout
        rail={
          <>
            <ArtifactTemplatePicker
              projectName={overview?.project.name}
              threadOptions={threadOptions}
              compareOptions={compareOptions}
              isSubmitting={createArtifact.isPending}
              onCreate={(request) => {
                void handleCreateArtifact(request)
              }}
            />

            <ArtifactList
              artifacts={artifacts}
              activeArtifactId={activeArtifactId}
              isLoading={artifactsLoading}
              isRegenerating={regenerateArtifact.isPending}
              onSelect={setActiveArtifactId}
              onRegenerate={(artifactId) => {
                void handleRegenerateArtifact(artifactId)
              }}
            />
          </>
        }
        detail={
          <ArtifactEditor
            artifact={selectedArtifact}
            isLoading={activeArtifactLoading}
            isRegenerating={regenerateArtifact.isPending}
            onRegenerate={(artifactId) => {
              void handleRegenerateArtifact(artifactId)
            }}
          />
        }
        railTitle="创建与选择"
        railDescription="先选模板，再切换已有产物。"
        railBadge={<Badge variant="outline">{artifacts.length}</Badge>}
        railWidth="minmax(320px, 0.9fr)"
        detailWidth="minmax(0, 1.6fr)"
      />
    </div>
  )
}
