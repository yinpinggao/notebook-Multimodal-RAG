'use client'

import { useParams } from 'next/navigation'
import { faArrowRotateRight, faSpinner } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { MemorySectionBoard } from '@/components/zhiyancang/memory/memory-section-board'
import {
  useDeleteProjectMemory,
  useRebuildProjectMemory,
  useUpdateProjectMemory,
} from '@/lib/hooks/use-project-memory'
import { useZycProjectDetail } from '@/lib/hooks/use-zyc-project-detail'
import { formatApiError } from '@/lib/utils/error-handler'

export default function ProjectMemoryPage() {
  const params = useParams()
  const projectId = String(params?.projectId || '')
  const { data, error, isLoading, meta } = useZycProjectDetail(projectId)
  const updateMemory = useUpdateProjectMemory(projectId)
  const deleteMemory = useDeleteProjectMemory(projectId)
  const rebuildMemory = useRebuildProjectMemory(projectId)

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Memory unavailable</AlertTitle>
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

  const isMutating =
    updateMemory.isPending || deleteMemory.isPending || rebuildMemory.isPending

  return (
    <div className="space-y-4">
      <div className="zyc-glass flex flex-wrap items-center justify-between gap-3 rounded-[24px] px-5 py-5">
        <div>
          <div className="text-sm font-medium text-white">Memory Governance</div>
          <p className="mt-1 text-sm leading-6 text-white/58">
            Draft, accept, freeze, deprecate, or rebuild project memory from the live evidence
            graph.
          </p>
        </div>

        <Button
          type="button"
          onClick={() => {
            void rebuildMemory.mutateAsync()
          }}
          disabled={rebuildMemory.isPending}
          className="rounded-full bg-white text-zinc-950 hover:bg-white/92"
        >
          {rebuildMemory.isPending ? (
            <FontAwesomeIcon icon={faSpinner} className="mr-2 animate-spin" />
          ) : (
            <FontAwesomeIcon icon={faArrowRotateRight} className="mr-2" />
          )}
          Rebuild Memory
        </Button>
      </div>

      {updateMemory.error || deleteMemory.error || rebuildMemory.error ? (
        <Alert variant="destructive">
          <AlertTitle>Memory action failed</AlertTitle>
          <AlertDescription>
            {formatApiError(updateMemory.error || deleteMemory.error || rebuildMemory.error)}
          </AlertDescription>
        </Alert>
      ) : null}

      <MemorySectionBoard
        items={data.memory}
        disabled={isMutating}
        onAccept={(item) => {
          void updateMemory.mutateAsync({
            memoryId: item.id,
            data: { status: 'accepted' },
          })
        }}
        onFreeze={(item) => {
          void updateMemory.mutateAsync({
            memoryId: item.id,
            data: { status: 'frozen' },
          })
        }}
        onDeprecate={(item) => {
          void updateMemory.mutateAsync({
            memoryId: item.id,
            data: { status: 'deprecated' },
          })
        }}
        onEdit={(item) => {
          const rawItem = meta.memories.find((memory) => memory.id === item.id)
          const nextText =
            typeof window === 'undefined'
              ? null
              : window.prompt('Edit memory', rawItem?.text || item.content)
          if (!nextText || !nextText.trim()) {
            return
          }
          void updateMemory.mutateAsync({
            memoryId: item.id,
            data: { text: nextText.trim() },
          })
        }}
        onDelete={(item) => {
          void deleteMemory.mutateAsync(item.id)
        }}
      />
    </div>
  )
}
