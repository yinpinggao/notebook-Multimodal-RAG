'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { AlertCircle, BrainCircuit, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'

import { MemoryConflictPanel } from '@/components/memory/memory-conflict-panel'
import { MemoryList } from '@/components/memory/memory-list'
import { MemoryReviewDialog } from '@/components/memory/memory-review-dialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { QUERY_KEYS } from '@/lib/api/query-client'
import {
  useDeleteProjectMemory,
  useProjectMemory,
  useRebuildProjectMemory,
  useUpdateProjectMemory,
} from '@/lib/hooks/use-project-memory'
import { projectIdToNotebookId } from '@/lib/project-alias'
import { MemoryRecordResponse, MemoryStatus } from '@/lib/types/api'
import { formatApiError } from '@/lib/utils/error-handler'

const REBUILD_POLL_MS = 2000
const REBUILD_POLL_WINDOW_MS = 12000

export default function ProjectMemoryPage() {
  const params = useParams()
  const queryClient = useQueryClient()
  const routeProjectId = params?.projectId ? String(params.projectId) : ''
  const projectId = projectIdToNotebookId(routeProjectId)

  const [activeMemory, setActiveMemory] = useState<MemoryRecordResponse | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [rebuildPolling, setRebuildPolling] = useState(false)

  const {
    data: memories = [],
    isLoading,
    error,
  } = useProjectMemory(projectId)
  const updateMemory = useUpdateProjectMemory(projectId)
  const deleteMemory = useDeleteProjectMemory(projectId)
  const rebuildMemory = useRebuildProjectMemory(projectId)

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

  const counts = useMemo(
    () => ({
      total: memories.length,
      draft: memories.filter((memory) => memory.status === 'draft').length,
      accepted: memories.filter((memory) => memory.status === 'accepted').length,
    }),
    [memories]
  )

  const topLevelError = error || updateMemory.error || deleteMemory.error || rebuildMemory.error

  const openReviewDialog = (memory: MemoryRecordResponse) => {
    setActiveMemory(memory)
    setDialogOpen(true)
  }

  const handleQuickAccept = async (memory: MemoryRecordResponse) => {
    try {
      await updateMemory.mutateAsync({
        memoryId: memory.id,
        data: {
          status: 'accepted',
        },
      })
    } catch {
      // Errors are rendered inline.
    }
  }

  const handleSaveMemory = async (payload: { text: string; status: MemoryStatus }) => {
    if (!activeMemory) {
      return
    }

    try {
      await updateMemory.mutateAsync({
        memoryId: activeMemory.id,
        data: payload,
      })
      setDialogOpen(false)
      setActiveMemory(null)
    } catch {
      // Errors are rendered inline.
    }
  }

  const handleDeleteMemory = async (memory: MemoryRecordResponse) => {
    const confirmed = window.confirm('删除后这条记忆会从当前项目移除。继续吗？')
    if (!confirmed) {
      return
    }

    try {
      await deleteMemory.mutateAsync(memory.id)
      if (activeMemory?.id === memory.id) {
        setDialogOpen(false)
        setActiveMemory(null)
      }
    } catch {
      // Errors are rendered inline.
    }
  }

  const handleRebuildMemory = async () => {
    try {
      await rebuildMemory.mutateAsync()
      setRebuildPolling(true)
    } catch {
      // Errors are rendered inline.
    }
  }

  return (
    <div className="space-y-6">
      <Card className="border-border/70">
        <CardHeader>
          <div className="flex items-center gap-2">
            <BrainCircuit className="h-4 w-4 text-muted-foreground" />
            <CardTitle>记忆中心</CardTitle>
          </div>
          <CardDescription>
            把项目长期记忆拉到台面上。先看来源，再决定接受、冻结、标记过时还是删除。
          </CardDescription>
        </CardHeader>
      </Card>

      {topLevelError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>记忆中心暂时不可用</AlertTitle>
          <AlertDescription>{formatApiError(topLevelError)}</AlertDescription>
        </Alert>
      ) : null}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">{counts.total} 条记忆</Badge>
          <Badge variant="secondary">{counts.draft} 条待确认</Badge>
          <Badge variant="outline">{counts.accepted} 条已接受</Badge>
        </div>

        <Button onClick={() => void handleRebuildMemory()} disabled={rebuildMemory.isPending}>
          <RefreshCw className="mr-2 h-4 w-4" />
          {rebuildMemory.isPending ? '重建中...' : '重建项目记忆'}
        </Button>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <MemoryList
          memories={memories}
          isLoading={isLoading}
          isUpdating={updateMemory.isPending}
          isDeleting={deleteMemory.isPending}
          onAccept={(memory) => {
            void handleQuickAccept(memory)
          }}
          onReview={openReviewDialog}
          onDelete={(memory) => {
            void handleDeleteMemory(memory)
          }}
        />

        <MemoryConflictPanel memories={memories} />
      </div>

      <MemoryReviewDialog
        memory={activeMemory}
        open={dialogOpen}
        isSaving={updateMemory.isPending}
        isDeleting={deleteMemory.isPending}
        onOpenChange={(open) => {
          setDialogOpen(open)
          if (!open) {
            setActiveMemory(null)
          }
        }}
        onSave={(payload) => {
          void handleSaveMemory(payload)
        }}
        onDelete={() => {
          if (activeMemory) {
            void handleDeleteMemory(activeMemory)
          }
        }}
      />
    </div>
  )
}
