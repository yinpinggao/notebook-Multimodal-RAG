'use client'

import { DragEvent, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  ChevronLeft,
  FileText,
  GripVertical,
  Pin,
  Plus,
  Search,
  StickyNote,
} from 'lucide-react'

import { NoteEditorDialog } from '@/app/(dashboard)/notebooks/components/NoteEditorDialog'
import { AddSourceDialog } from '@/components/sources/AddSourceDialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AssistantContextItem,
  AssistantContextMode,
  AssistantKnowledgeSelection,
  mergeAssistantSearchParams,
} from '@/lib/assistant-workspace'
import { useNotes } from '@/lib/hooks/use-notes'
import { useProjects } from '@/lib/hooks/use-projects'
import { useNotebookSources } from '@/lib/hooks/use-sources'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useModalManager } from '@/lib/hooks/use-modal-manager'
import { useAssistantWorkspaceStore } from '@/lib/stores/assistant-workspace-store'
import { NoteResponse, SourceListResponse } from '@/lib/types/api'
import { cn } from '@/lib/utils'

interface KnowledgePanelProps {
  projectId?: string
  className?: string
  isFocused?: boolean
  previewSelection?: AssistantKnowledgeSelection | null
  onPreviewSelect?: (selection: AssistantKnowledgeSelection) => void
}

type KnowledgeFilter = 'all' | 'sources' | 'notes'

function buildSourceContextItem(source: SourceListResponse): AssistantContextItem {
  const contextMode: AssistantContextMode =
    source.insights_count > 0 ? 'insights' : 'full'

  return {
    id: source.id,
    type: 'source',
    label: source.title || source.id,
    contextMode,
  }
}

function buildNoteContextItem(note: NoteResponse): AssistantContextItem {
  return {
    id: note.id,
    type: 'note',
    label: note.title || note.id,
    contextMode: 'full',
  }
}

export function KnowledgePanel({
  projectId,
  className,
  isFocused = false,
  previewSelection,
  onPreviewSelect,
}: KnowledgePanelProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { t } = useTranslation()
  const { openModal } = useModalManager()
  const {
    data: projects = [],
  } = useProjects(false)
  const {
    sources,
    isLoading: sourcesLoading,
  } = useNotebookSources(projectId || '')
  const { data: notes = [], isLoading: notesLoading } = useNotes(projectId)
  const {
    selectedContextItems,
    toggleContextItem,
    toggleKnowledgeCollapsed,
  } = useAssistantWorkspaceStore()

  const [searchValue, setSearchValue] = useState('')
  const [filter, setFilter] = useState<KnowledgeFilter>('all')
  const [sourceDialogOpen, setSourceDialogOpen] = useState(false)
  const [noteDialogOpen, setNoteDialogOpen] = useState(false)

  const normalizedQuery = searchValue.trim().toLowerCase()

  const selectedSet = useMemo(
    () =>
      new Set(selectedContextItems.map((item) => `${item.type}:${item.id}`)),
    [selectedContextItems]
  )

  const filteredSources = useMemo(() => {
    if (filter === 'notes') {
      return []
    }
    return sources.filter((source) => {
      if (!normalizedQuery) {
        return true
      }
      return `${source.title || ''} ${source.id}`.toLowerCase().includes(normalizedQuery)
    })
  }, [filter, normalizedQuery, sources])

  const filteredNotes = useMemo(() => {
    if (filter === 'sources') {
      return []
    }
    return notes.filter((note) => {
      if (!normalizedQuery) {
        return true
      }
      return `${note.title || ''} ${note.content || ''} ${note.id}`
        .toLowerCase()
        .includes(normalizedQuery)
    })
  }, [filter, normalizedQuery, notes])

  const handleProjectChange = (nextProjectId: string) => {
    router.replace(
      mergeAssistantSearchParams(searchParams, {
        projectId: nextProjectId,
        threadId: null,
      }),
      { scroll: false }
    )
  }

  const handleDragStart = (item: AssistantContextItem) => (event: DragEvent) => {
    event.dataTransfer.setData('application/x-assistant-context', JSON.stringify(item))
    event.dataTransfer.effectAllowed = 'copy'
  }

  const handleSourceOpen = (sourceId: string) => {
    if (onPreviewSelect) {
      onPreviewSelect({
        id: sourceId,
        type: 'source',
      })
      return
    }

    openModal('source', sourceId)
  }

  const handleNoteOpen = (noteId: string) => {
    if (onPreviewSelect) {
      onPreviewSelect({
        id: noteId,
        type: 'note',
      })
      return
    }

    openModal('note', noteId)
  }

  return (
    <>
      <section
        className={cn(
          'flex h-full min-h-0 flex-col border-r border-border/70 bg-background',
          isFocused && 'bg-muted/10',
          className
        )}
      >
        <div className="space-y-4 border-b border-border/70 px-4 py-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold">{t.assistant.knowledgeHub}</div>
              <div className="text-xs text-muted-foreground">
                {t.assistant.knowledgeHint}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="hidden lg:inline-flex"
                onClick={toggleKnowledgeCollapsed}
                aria-label={t.assistant.collapseKnowledge}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setNoteDialogOpen(true)}
                disabled={!projectId}
              >
                <StickyNote className="mr-2 h-4 w-4" />
                {t.common.note}
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={() => setSourceDialogOpen(true)}
                disabled={!projectId}
              >
                <Plus className="mr-2 h-4 w-4" />
                {t.common.source}
              </Button>
            </div>
          </div>

          <Select value={projectId} onValueChange={handleProjectChange} disabled={!projects.length}>
            <SelectTrigger>
              <SelectValue placeholder={t.assistant.selectProject} />
            </SelectTrigger>
            <SelectContent>
              {projects.map((project) => (
                <SelectItem key={project.id} value={project.id}>
                  {project.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchValue}
              onChange={(event) => setSearchValue(event.target.value)}
              placeholder={t.common.search}
              className="pl-9"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {(['all', 'sources', 'notes'] as KnowledgeFilter[]).map((value) => (
              <Button
                key={value}
                type="button"
                size="sm"
                variant={filter === value ? 'secondary' : 'outline'}
                onClick={() => setFilter(value)}
              >
                {value === 'all'
                  ? t.assistant.allKnowledge
                  : value === 'sources'
                    ? t.navigation.sources
                    : t.common.notes}
              </Button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          {!projectId ? (
            <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
              {t.assistant.selectProjectHint}
            </div>
          ) : null}

          {projectId ? (
            <div className="space-y-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold">{t.navigation.sources}</div>
                  <div className="text-xs text-muted-foreground">
                    {sourcesLoading ? t.common.loading : `${filteredSources.length}`}
                  </div>
                </div>

                {filteredSources.length === 0 ? (
                  <div className="rounded-md border border-dashed border-border/70 px-3 py-5 text-sm text-muted-foreground">
                    {t.sources.noSourcesYet}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {filteredSources.map((source) => {
                      const item = buildSourceContextItem(source)
                      const isSelected = selectedSet.has(`source:${source.id}`)
                      const isPreviewed =
                        previewSelection?.type === 'source' &&
                        previewSelection.id === source.id

                      return (
                        <div
                          key={source.id}
                          draggable
                          onDragStart={handleDragStart(item)}
                          className={cn(
                            'rounded-md border border-border/70 bg-card p-3',
                            onPreviewSelect && 'cursor-pointer',
                            isPreviewed && 'border-primary/50 bg-muted/30'
                          )}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <button
                              type="button"
                              className="min-w-0 flex-1 text-left"
                              onClick={() => handleSourceOpen(source.id)}
                            >
                              <div className="flex items-center gap-2">
                                <GripVertical className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                                <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                                <span className="truncate text-sm font-medium">
                                  {source.title || source.id}
                                </span>
                              </div>
                              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                <span>{source.embedded ? t.assistant.embeddedReady : t.assistant.embeddingPending}</span>
                                {source.insights_count > 0 ? (
                                  <span>{t.assistant.insightsCount.replace('{count}', String(source.insights_count))}</span>
                                ) : null}
                              </div>
                            </button>

                            <Button
                              type="button"
                              size="sm"
                              variant={isSelected ? 'secondary' : 'outline'}
                              onClick={() => toggleContextItem(item)}
                            >
                              <Pin className="mr-2 h-4 w-4" />
                              {isSelected ? t.assistant.inContext : t.assistant.addContext}
                            </Button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold">{t.common.notes}</div>
                  <div className="text-xs text-muted-foreground">
                    {notesLoading ? t.common.loading : `${filteredNotes.length}`}
                  </div>
                </div>

                {filteredNotes.length === 0 ? (
                  <div className="rounded-md border border-dashed border-border/70 px-3 py-5 text-sm text-muted-foreground">
                    {t.notebooks.noNotesYet}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {filteredNotes.map((note) => {
                      const item = buildNoteContextItem(note)
                      const isSelected = selectedSet.has(`note:${note.id}`)
                      const isPreviewed =
                        previewSelection?.type === 'note' &&
                        previewSelection.id === note.id

                      return (
                        <div
                          key={note.id}
                          draggable
                          onDragStart={handleDragStart(item)}
                          className={cn(
                            'rounded-md border border-border/70 bg-card p-3',
                            onPreviewSelect && 'cursor-pointer',
                            isPreviewed && 'border-primary/50 bg-muted/30'
                          )}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <button
                              type="button"
                              className="min-w-0 flex-1 text-left"
                              onClick={() => handleNoteOpen(note.id)}
                            >
                              <div className="flex items-center gap-2">
                                <GripVertical className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                                <StickyNote className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                                <span className="truncate text-sm font-medium">
                                  {note.title || t.sources.untitledNote}
                                </span>
                              </div>
                              <div className="mt-2 line-clamp-3 text-xs leading-5 text-muted-foreground">
                                {note.content || t.assistant.emptyNotePreview}
                              </div>
                            </button>

                            <Button
                              type="button"
                              size="sm"
                              variant={isSelected ? 'secondary' : 'outline'}
                              onClick={() => toggleContextItem(item)}
                            >
                              <Pin className="mr-2 h-4 w-4" />
                              {isSelected ? t.assistant.inContext : t.assistant.addContext}
                            </Button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </section>

      <AddSourceDialog
        open={sourceDialogOpen}
        onOpenChange={setSourceDialogOpen}
        defaultNotebookId={projectId}
      />

      <NoteEditorDialog
        open={noteDialogOpen}
        onOpenChange={setNoteDialogOpen}
        notebookId={projectId || ''}
      />
    </>
  )
}
