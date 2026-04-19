'use client'

import { useMemo } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  ArrowRight,
  BrainCircuit,
  FileText,
  Pin,
  Send,
  StickyNote,
  X,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AssistantContextItem,
  AssistantKnowledgeSelection,
  mergeAssistantSearchParams,
} from '@/lib/assistant-workspace'
import { useNotes } from '@/lib/hooks/use-notes'
import { useProjectMemory, useUpdateProjectMemory } from '@/lib/hooks/use-project-memory'
import { useNotebookSources, useSource } from '@/lib/hooks/use-sources'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useAssistantWorkspaceStore } from '@/lib/stores/assistant-workspace-store'
import { MemoryRecordResponse, MemoryStatus, NoteResponse, SourceListResponse } from '@/lib/types/api'
import { cn } from '@/lib/utils'

function buildKnowledgeContextItem(
  item: SourceListResponse | NoteResponse,
  type: 'source' | 'note'
): AssistantContextItem {
  if (type === 'source') {
    const source = item as SourceListResponse
    return {
      id: source.id,
      type,
      label: source.title || source.id,
      contextMode: source.insights_count > 0 ? 'insights' : 'full',
    }
  }

  const note = item as NoteResponse
  return {
    id: note.id,
    type,
    label: note.title || note.id,
    contextMode: 'full',
  }
}

function buildMemoryContextItem(memory: MemoryRecordResponse): AssistantContextItem {
  return {
    id: memory.id,
    type: 'memory',
    label: memory.text,
    contextMode: 'full',
  }
}

function useSelectedKnowledgeItem(
  projectId?: string,
  selection?: AssistantKnowledgeSelection | null
) {
  const { sources } = useNotebookSources(projectId || '')
  const { data: notes = [] } = useNotes(projectId)

  return useMemo(() => {
    if (selection?.type === 'source') {
      const source = sources.find((candidate) => candidate.id === selection.id)
      if (source) {
        return {
          type: 'source' as const,
          item: source,
          contextItem: buildKnowledgeContextItem(source, 'source'),
        }
      }
    }

    if (selection?.type === 'note') {
      const note = notes.find((candidate) => candidate.id === selection.id)
      if (note) {
        return {
          type: 'note' as const,
          item: note,
          contextItem: buildKnowledgeContextItem(note, 'note'),
        }
      }
    }

    if (sources[0]) {
      return {
        type: 'source' as const,
        item: sources[0],
        contextItem: buildKnowledgeContextItem(sources[0], 'source'),
      }
    }

    if (notes[0]) {
      return {
        type: 'note' as const,
        item: notes[0],
        contextItem: buildKnowledgeContextItem(notes[0], 'note'),
      }
    }

    return null
  }, [notes, selection, sources])
}

export function PinnedContextRail({
  className,
  ctaLabel,
}: {
  className?: string
  ctaLabel?: string
}) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { t } = useTranslation()
  const { selectedContextItems, removeContextItem } = useAssistantWorkspaceStore()

  return (
    <section
      className={cn(
        'flex h-full min-h-0 flex-col border-l border-border/70 bg-background',
        className
      )}
    >
      <div className="border-b border-border/70 px-4 py-4">
        <div className="text-sm font-semibold">{t.assistant.context}</div>
        <div className="mt-1 text-xs text-muted-foreground">
          {selectedContextItems.length > 0
            ? t.assistant.contextCountLabel.replace(
                '{count}',
                String(selectedContextItems.length)
              )
            : t.assistant.dropContextHint}
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {selectedContextItems.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
            {t.assistant.pinnedContextHint}
          </div>
        ) : (
          selectedContextItems.map((item) => (
            <div
              key={`${item.type}:${item.id}`}
              className="rounded-md border border-border/70 bg-card px-3 py-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">
                    {item.type}
                  </div>
                  <div className="mt-1 break-words text-sm">{item.label}</div>
                </div>
                <button
                  type="button"
                  aria-label={t.common.remove}
                  onClick={() => removeContextItem(item.type, item.id)}
                >
                  <X className="h-4 w-4 text-muted-foreground" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="border-t border-border/70 px-4 py-4">
        <Button
          className="w-full"
          onClick={() =>
            router.replace(
              mergeAssistantSearchParams(searchParams, {
                view: 'workspace',
              }),
              { scroll: false }
            )
          }
        >
          <Send className="mr-2 h-4 w-4" />
          {ctaLabel || t.assistant.workspace}
        </Button>
      </div>
    </section>
  )
}

export function KnowledgePreviewPanel({
  projectId,
  className,
  selectedItem,
}: {
  projectId?: string
  className?: string
  selectedItem?: AssistantKnowledgeSelection | null
}) {
  const { t } = useTranslation()
  const router = useRouter()
  const searchParams = useSearchParams()
  const { addContextItem, selectedContextItems, toggleContextItem } =
    useAssistantWorkspaceStore()
  const selected = useSelectedKnowledgeItem(projectId, selectedItem)
  const { data: sourceDetail } = useSource(
    selected?.type === 'source' ? selected.item.id : ''
  )

  const isPinned = selected
    ? selectedContextItems.some(
        (item) => item.type === selected.contextItem.type && item.id === selected.contextItem.id
      )
    : false

  const handleAskInWorkspace = () => {
    if (selected) {
      addContextItem(selected.contextItem)
    }

    router.replace(
      mergeAssistantSearchParams(searchParams, {
        view: 'workspace',
      }),
      { scroll: false }
    )
  }

  return (
    <section className={cn('flex h-full min-h-0 flex-col bg-background', className)}>
      <div className="border-b border-border/70 px-5 py-4">
        <div className="text-sm font-semibold">{t.assistant.previewTitle}</div>
        <div className="mt-1 text-xs text-muted-foreground">
          {t.assistant.previewHint}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5">
        {!selected ? (
          <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
            {t.assistant.selectProjectHint}
          </div>
        ) : selected.type === 'source' ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">
                <FileText className="mr-1 h-3.5 w-3.5" />
                {t.navigation.sources}
              </Badge>
              <Badge variant="secondary">
                {selected.item.embedded ? t.assistant.embeddedReady : t.assistant.embeddingPending}
              </Badge>
            </div>
            <div>
              <h2 className="text-xl font-semibold">
                {selected.item.title || selected.item.id}
              </h2>
              <div className="mt-2 text-sm text-muted-foreground">
                {selected.item.insights_count > 0
                  ? t.assistant.insightsCount.replace(
                      '{count}',
                      String(selected.item.insights_count)
                    )
                  : t.assistant.noInsightsYet}
              </div>
            </div>
            <div className="rounded-md border border-border/70 bg-card p-4">
              <div className="whitespace-pre-wrap text-sm leading-6">
                {sourceDetail?.full_text?.slice(0, 2400) ||
                  t.assistant.sourcePreviewUnavailable}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">
                <StickyNote className="mr-1 h-3.5 w-3.5" />
                {t.common.notes}
              </Badge>
            </div>
            <div>
              <h2 className="text-xl font-semibold">
                {selected.item.title || selected.item.id}
              </h2>
            </div>
            <div className="rounded-md border border-border/70 bg-card p-4 text-sm leading-6">
              {selected.item.content || t.assistant.emptyNotePreview}
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/70 px-5 py-4">
        {selected ? (
          <Button
            type="button"
            variant={isPinned ? 'secondary' : 'outline'}
            onClick={() => toggleContextItem(selected.contextItem)}
          >
            <Pin className="mr-2 h-4 w-4" />
            {isPinned ? t.assistant.inContext : t.assistant.addContext}
          </Button>
        ) : (
          <div />
        )}
        <Button onClick={handleAskInWorkspace}>
          {t.assistant.askInWorkspace}
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </section>
  )
}

export function WorkspaceSupportRail({
  projectId,
  className,
}: {
  projectId?: string
  className?: string
}) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { t } = useTranslation()
  const { data: memories = [] } = useProjectMemory(projectId || '')
  const { selectedContextItems, addContextItem } = useAssistantWorkspaceStore()

  const suggestedMemories = useMemo(
    () =>
      memories
        .filter(
          (memory) =>
            !selectedContextItems.some(
              (item) => item.type === 'memory' && item.id === memory.id
            )
        )
        .slice(0, 6),
    [memories, selectedContextItems]
  )

  return (
    <section
      className={cn(
        'flex h-full min-h-0 flex-col border-l border-border/70 bg-background',
        className
      )}
    >
      <div className="border-b border-border/70 px-4 py-4">
        <div className="text-sm font-semibold">{t.assistant.context}</div>
        <div className="mt-1 text-xs text-muted-foreground">
          {t.assistant.workspaceSupportHint}
        </div>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto px-4 py-4">
        <div className="space-y-3">
          <div className="text-xs font-medium text-muted-foreground">{t.assistant.context}</div>
          {selectedContextItems.length === 0 ? (
            <div className="rounded-md border border-dashed border-border/70 px-4 py-6 text-sm text-muted-foreground">
              {t.assistant.dropContextHint}
            </div>
          ) : (
            selectedContextItems.map((item) => (
              <div
                key={`${item.type}:${item.id}`}
                className="rounded-md border border-border/70 bg-card px-3 py-3 text-sm"
              >
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  {item.type}
                </div>
                <div className="mt-1 break-words">{item.label}</div>
              </div>
            ))
          )}
        </div>

        <div className="space-y-3">
          <div className="text-xs font-medium text-muted-foreground">
            {t.assistant.recommendedMemory}
          </div>
          {suggestedMemories.length === 0 ? (
            <div className="rounded-md border border-dashed border-border/70 px-4 py-6 text-sm text-muted-foreground">
              {t.assistant.noMemoryYet}
            </div>
          ) : (
            suggestedMemories.map((memory) => (
              <div
                key={memory.id}
                className="rounded-md border border-border/70 bg-card p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span>{memory.type}</span>
                      <span>{memory.status}</span>
                    </div>
                    <div className="mt-2 text-sm leading-6">{memory.text}</div>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => addContextItem(buildMemoryContextItem(memory))}
                  >
                    <Pin className="mr-2 h-4 w-4" />
                    {t.assistant.addContext}
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="border-t border-border/70 px-4 py-4">
        <Button
          className="w-full"
          variant="outline"
          onClick={() =>
            router.replace(
              mergeAssistantSearchParams(searchParams, {
                view: 'memory',
              }),
              { scroll: false }
            )
          }
        >
          <BrainCircuit className="mr-2 h-4 w-4" />
          {t.assistant.memoryManager}
        </Button>
      </div>
    </section>
  )
}

export function MemoryDetailPanel({
  projectId,
  className,
  selectedMemoryId,
}: {
  projectId?: string
  className?: string
  selectedMemoryId?: string | null
}) {
  const { t } = useTranslation()
  const { data: memories = [] } = useProjectMemory(projectId || '')
  const updateProjectMemory = useUpdateProjectMemory(projectId || '')
  const { selectedContextItems, toggleContextItem } = useAssistantWorkspaceStore()

  const activeMemory = useMemo(() => {
    if (selectedMemoryId) {
      return memories.find((memory) => memory.id === selectedMemoryId) || memories[0]
    }
    return memories[0]
  }, [memories, selectedMemoryId])

  const isPinned = activeMemory
    ? selectedContextItems.some(
        (item) => item.type === 'memory' && item.id === activeMemory.id
      )
    : false

  return (
    <section className={cn('flex h-full min-h-0 flex-col bg-background', className)}>
      <div className="border-b border-border/70 px-5 py-4">
        <div className="text-sm font-semibold">{t.assistant.memoryDetailTitle}</div>
        <div className="mt-1 text-xs text-muted-foreground">
          {t.assistant.memoryDetailHint}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5">
        {!activeMemory ? (
          <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
            {t.assistant.noMemoryYet}
          </div>
        ) : (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">{activeMemory.type}</Badge>
              <Badge variant="secondary">{activeMemory.status}</Badge>
              <Badge variant="outline">
                {Math.round(activeMemory.confidence * 100)}%
              </Badge>
            </div>

            <div className="rounded-md border border-border/70 bg-card p-4">
              <div className="text-sm leading-6">{activeMemory.text}</div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <div className="text-xs font-medium text-muted-foreground">
                  {t.assistant.memoryStatus}
                </div>
                <Select
                  value={activeMemory.status}
                  onValueChange={(value) =>
                    updateProjectMemory.mutate({
                      memoryId: activeMemory.id,
                      data: { status: value as MemoryStatus },
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft">{t.assistant.memoryStatusDraft}</SelectItem>
                    <SelectItem value="accepted">{t.assistant.memoryStatusAccepted}</SelectItem>
                    <SelectItem value="frozen">{t.assistant.memoryStatusFrozen}</SelectItem>
                    <SelectItem value="deprecated">{t.assistant.memoryStatusDeprecated}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <div className="text-xs font-medium text-muted-foreground">
                  {t.assistant.decayLabel}
                </div>
                <div className="rounded-md border border-border/70 bg-card px-3 py-2 text-sm">
                  {activeMemory.decay_policy}
                </div>
              </div>
            </div>

            <Button
              type="button"
              variant={isPinned ? 'secondary' : 'outline'}
              onClick={() => toggleContextItem(buildMemoryContextItem(activeMemory))}
            >
              <Pin className="mr-2 h-4 w-4" />
              {isPinned ? t.assistant.inContext : t.assistant.addContext}
            </Button>
          </div>
        )}
      </div>
    </section>
  )
}

export function MemorySourceRefsRail({
  projectId,
  className,
  selectedMemoryId,
}: {
  projectId?: string
  className?: string
  selectedMemoryId?: string | null
}) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { t } = useTranslation()
  const { data: memories = [] } = useProjectMemory(projectId || '')
  const { addContextItem } = useAssistantWorkspaceStore()

  const activeMemory = useMemo(() => {
    if (selectedMemoryId) {
      return memories.find((memory) => memory.id === selectedMemoryId) || memories[0]
    }
    return memories[0]
  }, [memories, selectedMemoryId])

  return (
    <section
      className={cn(
        'flex h-full min-h-0 flex-col border-l border-border/70 bg-background',
        className
      )}
    >
      <div className="border-b border-border/70 px-4 py-4">
        <div className="text-sm font-semibold">{t.assistant.sourceReferencesTitle}</div>
        <div className="mt-1 text-xs text-muted-foreground">
          {t.assistant.sourceReferencesHint}
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {!activeMemory ? (
          <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
            {t.assistant.noMemoryYet}
          </div>
        ) : activeMemory.source_refs.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
            {t.assistant.noMemoryRefs}
          </div>
        ) : (
          activeMemory.source_refs.map((ref) => (
            <div
              key={`${ref.source_id}:${ref.internal_ref}`}
              className="rounded-md border border-border/70 bg-card p-3"
            >
              <div className="text-sm font-medium">
                {ref.source_name || ref.source_id}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                {ref.page_no ? `Page ${ref.page_no}` : ref.internal_ref}
              </div>
              {ref.citation_text ? (
                <div className="mt-2 text-sm leading-6 text-muted-foreground">
                  {ref.citation_text}
                </div>
              ) : null}
            </div>
          ))
        )}
      </div>

      <div className="border-t border-border/70 px-4 py-4">
        <Button
          className="w-full"
          onClick={() => {
            if (activeMemory) {
              addContextItem(buildMemoryContextItem(activeMemory))
            }
            router.replace(
              mergeAssistantSearchParams(searchParams, {
                view: 'workspace',
              }),
              { scroll: false }
            )
          }}
        >
          <ArrowRight className="mr-2 h-4 w-4" />
          {t.assistant.sendToWorkspace}
        </Button>
      </div>
    </section>
  )
}
