'use client'

import { useEffect } from 'react'
import { useParams } from 'next/navigation'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { MobileDrawer } from '@/components/zhiyancang/layout/mobile-drawer'
import { AgentCenterGrid } from '@/components/zhiyancang/workspace/agent-center-grid'
import { WorkspaceFeedbackPanel } from '@/components/zhiyancang/workspace/workspace-feedback-panel'
import { WorkspaceLeftPanel } from '@/components/zhiyancang/workspace/workspace-left-panel'
import { Button } from '@/components/ui/button'
import { useCreateProjectArtifact } from '@/lib/hooks/use-project-artifacts'
import { useCreateProjectMemory } from '@/lib/hooks/use-project-memory'
import { useMediaQuery } from '@/lib/hooks/use-media-query'
import { useZycProjectDetail } from '@/lib/hooks/use-zyc-project-detail'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import { formatApiError } from '@/lib/utils/error-handler'

export default function ProjectWorkspacePage() {
  const params = useParams()
  const projectId = String(params?.projectId || '')
  const { data, error, isLoading, meta } = useZycProjectDetail(projectId)
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const isMobile = useMediaQuery('(max-width: 639px)')
  const createMemory = useCreateProjectMemory(projectId)
  const createArtifact = useCreateProjectArtifact(projectId)
  const {
    workspaceLeftOpen,
    workspaceRightOpen,
    workspaceMemoryScope,
    workspaceRetrievalMode,
    setWorkspaceLeftOpen,
    setWorkspaceMemoryScope,
    setWorkspaceRetrievalMode,
    setWorkspaceRightOpen,
  } = useZycUIStore()

  useEffect(() => {
    if (!data) {
      return
    }

    const nextRetrievalMode = data.workspace.retrievalModes.includes(workspaceRetrievalMode)
      ? workspaceRetrievalMode
      : data.workspace.retrievalModes[0]
    const nextMemoryScope = data.workspace.memoryScopes.includes(workspaceMemoryScope)
      ? workspaceMemoryScope
      : data.workspace.memoryScopes[0]

    if (nextRetrievalMode && nextRetrievalMode !== workspaceRetrievalMode) {
      setWorkspaceRetrievalMode(nextRetrievalMode)
    }

    if (nextMemoryScope && nextMemoryScope !== workspaceMemoryScope) {
      setWorkspaceMemoryScope(nextMemoryScope)
    }
  }, [
    data,
    setWorkspaceMemoryScope,
    setWorkspaceRetrievalMode,
    workspaceMemoryScope,
    workspaceRetrievalMode,
  ])

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Workspace unavailable</AlertTitle>
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

  const leftPanel = <WorkspaceLeftPanel workspace={data.workspace} />
  const rightPanel = (
    <WorkspaceFeedbackPanel
      workspace={data.workspace}
      isSaving={createMemory.isPending || createArtifact.isPending}
      onSaveMemory={() => {
        const response = meta.activeThread?.latest_response
        const text = response?.answer || meta.activeThread?.last_answer_preview
        if (!text) {
          return
        }
        void createMemory.mutateAsync({
          text,
          type: 'fact',
          status: 'draft',
          scope: 'project',
          source_refs:
            response?.evidence_cards.slice(0, 5).map((card) => ({
              source_id: card.source_id,
              source_name: card.source_name,
              page_no: card.page_no || undefined,
              internal_ref: card.internal_ref,
              citation_text: card.citation_text,
            })) || [],
        })
      }}
      onSaveArtifact={() => {
        if (!meta.activeThreadId) {
          return
        }
        void createArtifact.mutateAsync({
          artifact_type: 'qa_cards',
          origin_kind: 'thread',
          origin_id: meta.activeThreadId,
        })
      }}
    />
  )

  return (
    <div className="space-y-4">
      {createMemory.error || createArtifact.error ? (
        <Alert variant="destructive">
          <AlertTitle>Workspace action failed</AlertTitle>
          <AlertDescription>
            {formatApiError(createMemory.error || createArtifact.error)}
          </AlertDescription>
        </Alert>
      ) : null}

      {!isDesktop ? (
        <div className="flex flex-wrap gap-3">
          <Button
            onClick={() => setWorkspaceLeftOpen(true)}
            className="rounded-full bg-white text-zinc-950 hover:bg-white/92"
          >
            Controls
          </Button>
          <Button
            onClick={() => setWorkspaceRightOpen(true)}
            variant="outline"
            className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
          >
            Feedback
          </Button>
        </div>
      ) : null}

      {isDesktop ? (
        <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)_340px]">
          {leftPanel}
          <AgentCenterGrid workspace={data.workspace} />
          {rightPanel}
        </div>
      ) : (
        <>
          <AgentCenterGrid workspace={data.workspace} />
          {isMobile ? (
            <div className="sticky bottom-4 z-30 flex justify-center">
              <div className="zyc-glass flex gap-3 rounded-full px-3 py-3">
                <Button
                  onClick={() => setWorkspaceLeftOpen(true)}
                  className="rounded-full bg-white text-zinc-950 hover:bg-white/92"
                >
                  Controls
                </Button>
                <Button
                  onClick={() => setWorkspaceRightOpen(true)}
                  variant="outline"
                  className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
                >
                  Feedback
                </Button>
              </div>
            </div>
          ) : null}
        </>
      )}

      <MobileDrawer
        open={workspaceLeftOpen}
        onOpenChange={setWorkspaceLeftOpen}
        side={isMobile ? 'bottom' : 'left'}
        title="Workspace Controls"
        description="Tasks, pinned evidence, retrieval mode, memory scope, and tool switches."
      >
        {leftPanel}
      </MobileDrawer>

      <MobileDrawer
        open={workspaceRightOpen}
        onOpenChange={setWorkspaceRightOpen}
        side={isMobile ? 'bottom' : 'right'}
        title="Workspace Feedback"
        description="Citations, run trace, logs, and save actions."
      >
        {rightPanel}
      </MobileDrawer>
    </div>
  )
}
