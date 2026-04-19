'use client'

import { ChangeEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import {
  BrainCircuit,
  ChevronRight,
  Download,
  Filter,
  Pin,
  RefreshCw,
  Upload,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { QUERY_KEYS } from '@/lib/api/query-client'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AssistantContextItem,
} from '@/lib/assistant-workspace'
import {
  useCreateProjectMemory,
  useProjectMemory,
  useRebuildProjectMemory,
} from '@/lib/hooks/use-project-memory'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useAssistantWorkspaceStore } from '@/lib/stores/assistant-workspace-store'
import {
  MemoryRecordResponse,
  MemoryStatus,
  MemoryType,
} from '@/lib/types/api'
import { cn } from '@/lib/utils'

interface MemoryPanelProps {
  projectId?: string
  className?: string
  isFocused?: boolean
  selectedMemoryId?: string | null
  onSelectMemory?: (memoryId: string) => void
}

type MemoryViewMode = 'list' | 'timeline'

const REBUILD_POLL_MS = 2000
const REBUILD_POLL_WINDOW_MS = 12000

function buildMemoryContextItem(memory: MemoryRecordResponse): AssistantContextItem {
  return {
    id: memory.id,
    type: 'memory',
    label: memory.text,
    contextMode: 'full',
  }
}

export function MemoryPanel({
  projectId,
  className,
  isFocused = false,
  selectedMemoryId,
  onSelectMemory,
}: MemoryPanelProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const {
    data: memories = [],
    isLoading,
  } = useProjectMemory(projectId || '')
  const rebuildMemory = useRebuildProjectMemory(projectId || '')
  const createMemory = useCreateProjectMemory(projectId || '')
  const {
    selectedContextItems,
    toggleContextItem,
    toggleMemoryCollapsed,
  } = useAssistantWorkspaceStore()

  const [searchValue, setSearchValue] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | MemoryStatus>('all')
  const [typeFilter, setTypeFilter] = useState<'all' | MemoryType>('all')
  const [viewMode, setViewMode] = useState<MemoryViewMode>('list')
  const [rebuildPolling, setRebuildPolling] = useState(false)

  useEffect(() => {
    if (!rebuildPolling || !projectId) {
      return
    }

    const intervalId = window.setInterval(() => {
      void queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectMemory(projectId),
      })
      void queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectOverview(projectId),
      })
      void queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projects,
      })
    }, REBUILD_POLL_MS)
    const timeoutId = window.setTimeout(() => {
      setRebuildPolling(false)
    }, REBUILD_POLL_WINDOW_MS)

    return () => {
      window.clearInterval(intervalId)
      window.clearTimeout(timeoutId)
    }
  }, [projectId, queryClient, rebuildPolling])

  const selectedSet = useMemo(
    () =>
      new Set(selectedContextItems.map((item) => `${item.type}:${item.id}`)),
    [selectedContextItems]
  )

  const filteredMemories = useMemo(() => {
    const normalizedQuery = searchValue.trim().toLowerCase()

    return memories.filter((memory) => {
      if (statusFilter !== 'all' && memory.status !== statusFilter) {
        return false
      }
      if (typeFilter !== 'all' && memory.type !== typeFilter) {
        return false
      }
      if (!normalizedQuery) {
        return true
      }
      return `${memory.text} ${memory.type} ${memory.status}`
        .toLowerCase()
        .includes(normalizedQuery)
    })
  }, [memories, searchValue, statusFilter, typeFilter])

  const timelineGroups = useMemo(() => {
    const groups = new Map<string, MemoryRecordResponse[]>()
    filteredMemories.forEach((memory) => {
      const key = `${memory.status}:${memory.type}`
      const current = groups.get(key) || []
      current.push(memory)
      groups.set(key, current)
    })
    return [...groups.entries()]
  }, [filteredMemories])

  const handleExport = () => {
    if (!projectId) {
      return
    }

    const blob = new Blob([JSON.stringify(memories, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${projectId.replace(/[:/]/g, '_')}-memory.json`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  const handleImportFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !projectId) {
      return
    }

    const raw = await file.text()
    const payload = JSON.parse(raw)
    const rows = Array.isArray(payload) ? payload : []

    for (const row of rows) {
      if (!row?.text || !row?.type) {
        continue
      }

      await createMemory.mutateAsync({
        text: String(row.text),
        type: row.type as MemoryType,
        status: 'draft',
        scope: 'project',
        source_refs: Array.isArray(row.source_refs) ? row.source_refs : [],
      })
    }

    event.target.value = ''
  }

  const renderCard = (memory: MemoryRecordResponse) => {
    const isSelected = selectedSet.has(`memory:${memory.id}`)
    const item = buildMemoryContextItem(memory)

    return (
      <div
        key={memory.id}
        draggable
        onClick={() => onSelectMemory?.(memory.id)}
        onDragStart={(event) => {
          event.dataTransfer.setData(
            'application/x-assistant-context',
            JSON.stringify(item)
          )
          event.dataTransfer.effectAllowed = 'copy'
        }}
        className={cn(
          'rounded-md border border-border/70 bg-card p-3',
          onSelectMemory && 'cursor-pointer',
          selectedMemoryId === memory.id && 'border-primary/50 bg-muted/30'
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span>{memory.type}</span>
              <span>{memory.status}</span>
              <span>{Math.round(memory.confidence * 100)}%</span>
            </div>
            <div className="mt-2 text-sm leading-6">{memory.text}</div>
            {memory.source_refs.length > 0 ? (
              <div className="mt-2 text-xs text-muted-foreground">
                {memory.source_refs[0]?.citation_text || memory.source_refs[0]?.internal_ref}
              </div>
            ) : null}
          </div>

          <Button
            type="button"
            size="sm"
            variant={isSelected ? 'secondary' : 'outline'}
            onClick={(event) => {
              event.stopPropagation()
              toggleContextItem(item)
            }}
          >
            <Pin className="mr-2 h-4 w-4" />
            {isSelected ? t.assistant.inContext : t.assistant.addContext}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <section
      className={cn(
        'flex h-full min-h-0 flex-col border-l border-border/70 bg-background',
        isFocused && 'bg-muted/10',
        className
      )}
    >
      <div className="space-y-4 border-b border-border/70 px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">{t.assistant.memoryManager}</div>
            <div className="text-xs text-muted-foreground">
              {t.assistant.memoryHint}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="hidden lg:inline-flex"
              onClick={toggleMemoryCollapsed}
              aria-label={t.assistant.collapseMemory}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={!projectId || memories.length === 0}
            >
              <Download className="mr-2 h-4 w-4" />
              {t.assistant.exportMemory}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleImportClick}
              disabled={!projectId || createMemory.isPending}
            >
              <Upload className="mr-2 h-4 w-4" />
              {t.assistant.importMemory}
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => {
                rebuildMemory.mutate(undefined, {
                  onSuccess: () => setRebuildPolling(true),
                })
              }}
              disabled={!projectId || rebuildMemory.isPending}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              {t.assistant.refreshMemory}
            </Button>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_140px_140px]">
          <Input
            value={searchValue}
            onChange={(event) => setSearchValue(event.target.value)}
            placeholder={t.assistant.searchMemory}
          />
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as 'all' | MemoryStatus)}>
            <SelectTrigger>
              <Filter className="mr-2 h-4 w-4 text-muted-foreground" />
              <SelectValue placeholder={t.assistant.memoryStatus} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t.assistant.allStatus}</SelectItem>
              <SelectItem value="draft">{t.assistant.memoryStatusDraft}</SelectItem>
              <SelectItem value="accepted">{t.assistant.memoryStatusAccepted}</SelectItem>
              <SelectItem value="frozen">{t.assistant.memoryStatusFrozen}</SelectItem>
              <SelectItem value="deprecated">{t.assistant.memoryStatusDeprecated}</SelectItem>
            </SelectContent>
          </Select>
          <Select value={typeFilter} onValueChange={(value) => setTypeFilter(value as 'all' | MemoryType)}>
            <SelectTrigger>
              <BrainCircuit className="mr-2 h-4 w-4 text-muted-foreground" />
              <SelectValue placeholder={t.common.type} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t.assistant.allTypes}</SelectItem>
              <SelectItem value="fact">{t.assistant.memoryTypeFact}</SelectItem>
              <SelectItem value="term">{t.assistant.memoryTypeTerm}</SelectItem>
              <SelectItem value="decision">{t.assistant.memoryTypeDecision}</SelectItem>
              <SelectItem value="risk">{t.assistant.memoryTypeRisk}</SelectItem>
              <SelectItem value="preference">{t.assistant.memoryTypePreference}</SelectItem>
              <SelectItem value="question">{t.assistant.memoryTypeQuestion}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant={viewMode === 'list' ? 'secondary' : 'outline'}
            onClick={() => setViewMode('list')}
          >
            {t.assistant.listView}
          </Button>
          <Button
            type="button"
            size="sm"
            variant={viewMode === 'timeline' ? 'secondary' : 'outline'}
            onClick={() => setViewMode('timeline')}
          >
            {t.assistant.timelineView}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {!projectId ? (
          <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
            {t.assistant.selectProjectHint}
          </div>
        ) : isLoading ? (
          <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
            {t.common.loading}
          </div>
        ) : filteredMemories.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
            {t.assistant.noMemoryYet}
          </div>
        ) : viewMode === 'list' ? (
          <div className="space-y-3">{filteredMemories.map(renderCard)}</div>
        ) : (
          <div className="space-y-6">
            {timelineGroups.map(([groupKey, items]) => (
              <div key={groupKey} className="space-y-3">
                <div className="text-sm font-semibold">{groupKey}</div>
                <div className="space-y-3">
                  {items.map(renderCard)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="application/json"
        className="hidden"
        onChange={(event) => {
          void handleImportFile(event)
        }}
      />
    </section>
  )
}
