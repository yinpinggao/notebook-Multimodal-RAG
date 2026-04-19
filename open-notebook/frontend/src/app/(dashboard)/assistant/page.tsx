'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { BrainCircuit, FileText } from 'lucide-react'

import { AgentPanel } from '@/components/harness/AgentPanel'
import {
  KnowledgePreviewPanel,
  MemoryDetailPanel,
  MemorySourceRefsRail,
  PinnedContextRail,
  WorkspaceSupportRail,
} from '@/components/harness/AssistantViewPanels'
import { KnowledgePanel } from '@/components/harness/KnowledgePanel'
import { MemoryPanel } from '@/components/harness/MemoryPanel'
import { Button } from '@/components/ui/button'
import {
  AssistantKnowledgeSelection,
  sanitizeAssistantView,
} from '@/lib/assistant-workspace'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import { useIsDesktop } from '@/lib/hooks/use-media-query'
import { useProjects } from '@/lib/hooks/use-projects'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useAssistantWorkspaceStore } from '@/lib/stores/assistant-workspace-store'
import { cn } from '@/lib/utils'

export default function AssistantPage() {
  const { t } = useTranslation()
  const isDesktop = useIsDesktop()
  const { openNotebookDialog } = useCreateDialogs()
  const { data: projects = [], isLoading } = useProjects(false)
  const {
    currentProjectId,
    currentView,
    knowledgeCollapsed,
    memoryCollapsed,
    setKnowledgeCollapsed,
    setMemoryCollapsed,
  } = useAssistantWorkspaceStore()
  const resolvedView = sanitizeAssistantView(currentView)
  const [selectedKnowledgeItem, setSelectedKnowledgeItem] =
    useState<AssistantKnowledgeSelection | null>(null)
  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null)

  useEffect(() => {
    setSelectedKnowledgeItem(null)
    setSelectedMemoryId(null)
  }, [currentProjectId])

  if (!isLoading && projects.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <div className="max-w-xl space-y-4 rounded-md border border-dashed border-border/70 px-6 py-10 text-center">
          <div className="text-xl font-semibold">{t.assistant.emptyWorkspaceTitle}</div>
          <div className="text-sm leading-6 text-muted-foreground">
            {t.assistant.emptyWorkspaceDescription}
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            <Button onClick={openNotebookDialog}>{t.assistant.createProject}</Button>
            <Button asChild variant="outline">
              <Link href="/projects">{t.navigation.projects}</Link>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  const renderWorkspaceDesktop = () => (
    <>
      {knowledgeCollapsed ? (
        <button
          type="button"
          className="flex w-12 items-center justify-center border-r border-border/70 bg-card text-xs text-muted-foreground"
          onClick={() => setKnowledgeCollapsed(false)}
        >
          <div className="flex flex-col items-center gap-3 py-6">
            <FileText className="h-4 w-4" />
            <span style={{ writingMode: 'vertical-rl', textOrientation: 'mixed' }}>
              {t.assistant.knowledgeHub}
            </span>
          </div>
        </button>
      ) : (
        <KnowledgePanel
          projectId={currentProjectId}
          className={cn('w-[22rem] transition-all duration-200')}
        />
      )}
      <AgentPanel projectId={currentProjectId} className="min-w-0 flex-1" />
      {memoryCollapsed ? (
        <button
          type="button"
          className="flex w-12 items-center justify-center border-l border-border/70 bg-card text-xs text-muted-foreground"
          onClick={() => setMemoryCollapsed(false)}
        >
          <div className="flex flex-col items-center gap-3 py-6">
            <BrainCircuit className="h-4 w-4" />
            <span style={{ writingMode: 'vertical-rl', textOrientation: 'mixed' }}>
              {t.assistant.memoryManager}
            </span>
          </div>
        </button>
      ) : (
        <WorkspaceSupportRail
          projectId={currentProjectId}
          className={cn('w-[24rem] transition-all duration-200')}
        />
      )}
    </>
  )

  const renderKnowledgeDesktop = () => (
    <>
      <KnowledgePanel
        projectId={currentProjectId}
        previewSelection={selectedKnowledgeItem}
        onPreviewSelect={setSelectedKnowledgeItem}
        isFocused
        className="w-[28rem] border-r border-border/70"
      />
      <KnowledgePreviewPanel
        projectId={currentProjectId}
        selectedItem={selectedKnowledgeItem}
        className="min-w-0 flex-1 border-r border-border/70"
      />
      <PinnedContextRail
        className="w-[22rem]"
        ctaLabel={t.assistant.askInWorkspace}
      />
    </>
  )

  const renderMemoryDesktop = () => (
    <>
      <MemoryPanel
        projectId={currentProjectId}
        selectedMemoryId={selectedMemoryId}
        onSelectMemory={setSelectedMemoryId}
        isFocused
        className="w-[26rem] border-l-0 border-r border-border/70"
      />
      <MemoryDetailPanel
        projectId={currentProjectId}
        selectedMemoryId={selectedMemoryId}
        className="min-w-0 flex-1 border-r border-border/70"
      />
      <MemorySourceRefsRail
        projectId={currentProjectId}
        selectedMemoryId={selectedMemoryId}
        className="w-[24rem]"
      />
    </>
  )

  const renderMobileView = () => {
    if (resolvedView === 'knowledge') {
      return (
        <div className="flex min-h-0 flex-1 flex-col overflow-auto">
          <div className="min-h-[60vh]">
            <KnowledgePanel
              projectId={currentProjectId}
              previewSelection={selectedKnowledgeItem}
              onPreviewSelect={setSelectedKnowledgeItem}
              className="h-full border-r-0"
            />
          </div>
          <KnowledgePreviewPanel
            projectId={currentProjectId}
            selectedItem={selectedKnowledgeItem}
            className="min-h-[24rem]"
          />
        </div>
      )
    }

    if (resolvedView === 'memory') {
      return (
        <div className="flex min-h-0 flex-1 flex-col overflow-auto">
          <div className="min-h-[60vh]">
            <MemoryPanel
              projectId={currentProjectId}
              selectedMemoryId={selectedMemoryId}
              onSelectMemory={setSelectedMemoryId}
              className="h-full border-l-0"
            />
          </div>
          <MemoryDetailPanel
            projectId={currentProjectId}
            selectedMemoryId={selectedMemoryId}
            className="min-h-[24rem]"
          />
        </div>
      )
    }

    return <AgentPanel projectId={currentProjectId} className="h-full" />
  }

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden">
      {isDesktop ? (
        resolvedView === 'knowledge'
          ? renderKnowledgeDesktop()
          : resolvedView === 'memory'
            ? renderMemoryDesktop()
            : renderWorkspaceDesktop()
      ) : (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{renderMobileView()}</div>
      )}
    </div>
  )
}
