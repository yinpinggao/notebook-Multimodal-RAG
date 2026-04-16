'use client'

import { useState, useMemo } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { vragApi } from '@/lib/api/vrag'
import { toast } from 'sonner'
import { SourceListResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Loader2,
  FileText,
  Globe,
  File,
  RefreshCw,
  Zap,
} from 'lucide-react'

interface IndexingDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sources: SourceListResponse[]
}

type IndexingStatus = 'idle' | 'indexing' | 'indexed' | 'error' | 'rebuilding' | 'rebuilt' | 'rebuild-error'

interface SourceIndexState {
  id: string
  status: IndexingStatus
  message?: string
}

export function IndexingDialog({
  open,
  onOpenChange,
  sources,
}: IndexingDialogProps) {
  const { t } = useTranslation()

  // Source selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  // Indexing state per source
  const [indexStates, setIndexStates] = useState<Record<string, SourceIndexState>>({})

  // Check if any indexing is in progress
  const isIndexing = useMemo(() => {
    return Object.values(indexStates).some(
      (s) => s.status === 'indexing' || s.status === 'rebuilding'
    )
  }, [indexStates])

  // Get source type icon and label
  const getSourceType = (source: SourceListResponse) => {
    const asset = source.asset
    if (asset?.url) {
      return { icon: Globe, label: 'URL' }
    }
    const filePath = asset?.file_path || ''
    if (filePath.toLowerCase().endsWith('.pdf')) {
      return { icon: FileText, label: 'PDF' }
    }
    return { icon: File, label: 'File' }
  }

  // Get indexing status for a source
  const getStatus = (sourceId: string): IndexingStatus => {
    return indexStates[sourceId]?.status || 'idle'
  }

  // Get status badge variant
  const getStatusBadge = (status: IndexingStatus) => {
    switch (status) {
      case 'indexed':
      case 'rebuilt':
        return <Badge className="bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20">{t.vrag?.index?.indexed || 'Indexed'}</Badge>
      case 'error':
      case 'rebuild-error':
        return <Badge className="bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20">{t.vrag?.index?.error || 'Error'}</Badge>
      case 'indexing':
      case 'rebuilding':
        return <Badge variant="secondary" className="gap-1"><Loader2 className="h-3 w-3 animate-spin" />{t.vrag?.index?.indexing || 'Indexing'}</Badge>
      default:
        return <Badge variant="outline" className="text-muted-foreground">{t.vrag?.index?.notIndexed || 'Not indexed'}</Badge>
    }
  }

  // Toggle source selection
  const toggleSource = (sourceId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(sourceId)) {
        next.delete(sourceId)
      } else {
        next.add(sourceId)
      }
      return next
    })
  }

  // Select all / deselect all
  const toggleSelectAll = () => {
    if (selectedIds.size === sources.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(sources.map((s) => s.id)))
    }
  }

  // Index selected sources
  const handleIndex = async () => {
    if (selectedIds.size === 0) return

    const toIndex = sources.filter((s) => selectedIds.has(s.id))
    for (const source of toIndex) {
      const state: SourceIndexState = { id: source.id, status: 'indexing' }
      setIndexStates((prev) => ({ ...prev, [source.id]: state }))

      try {
        const asset = source.asset || {}
        const sourcePath = asset.file_path || asset.url || ''
        const sourceType = asset.url ? 'url' : 'pdf'

        const result = await vragApi.indexSource(
          source.id,
          sourcePath,
          sourceType,
          true
        )

        const result_ = result.indexing_result
        if (result_ && result_.errors > 0) {
          setIndexStates((prev) => ({
            ...prev,
            [source.id]: {
              id: source.id,
              status: 'error',
              message: `${result_.indexed}/${result_.total} indexed, ${result_.errors} errors`,
            },
          }))
          toast.error(t.vrag?.index?.indexError || `Indexing error for ${source.title || source.id}`, {
            description: `${result_.indexed}/${result_.total} chunks indexed, ${result_.errors} errors`,
          })
        } else {
          setIndexStates((prev) => ({
            ...prev,
            [source.id]: { id: source.id, status: 'indexed' },
          }))
          toast.success(t.vrag?.index?.indexSuccess || `Indexing complete for ${source.title || source.id}`, {
            description: `${result_?.indexed || 0}/${result_?.total || 0} chunks indexed`,
          })
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        setIndexStates((prev) => ({
          ...prev,
          [source.id]: { id: source.id, status: 'error', message: msg },
        }))
        toast.error(t.vrag?.index?.indexError || `Indexing failed for ${source.title || source.id}`, {
          description: msg,
        })
      }
    }

    // Clear selection after indexing
    setSelectedIds(new Set())
  }

  // Rebuild index for selected sources
  const handleRebuild = async () => {
    if (selectedIds.size === 0) return

    const toRebuild = sources.filter((s) => selectedIds.has(s.id))
    for (const source of toRebuild) {
      setIndexStates((prev) => ({ ...prev, [source.id]: { id: source.id, status: 'rebuilding' } }))

      try {
        const result = await vragApi.rebuildIndex(source.id, true)
        const result_ = result.rebuild_result

        if (result_ && result_.errors > 0) {
          setIndexStates((prev) => ({
            ...prev,
            [source.id]: {
              id: source.id,
              status: 'rebuild-error',
              message: `${result_.rebuilt}/${result_.total} rebuilt, ${result_.errors} errors`,
            },
          }))
        } else {
          setIndexStates((prev) => ({
            ...prev,
            [source.id]: { id: source.id, status: 'rebuilt' },
          }))
          toast.success(t.vrag?.index?.rebuildSuccess || `Rebuild complete for ${source.title || source.id}`, {
            description: `${result_?.rebuilt || 0}/${result_?.total || 0} chunks rebuilt`,
          })
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        setIndexStates((prev) => ({
          ...prev,
          [source.id]: { id: source.id, status: 'rebuild-error', message: msg },
        }))
        toast.error(t.vrag?.index?.rebuildError || `Rebuild failed for ${source.title || source.id}`, {
          description: msg,
        })
      }
    }

    setSelectedIds(new Set())
  }

  // Reset all status when dialog opens
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setSelectedIds(new Set())
      setIndexStates({})
    }
    onOpenChange(newOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-amber-500" />
            {t.vrag?.index?.title || 'Index Sources for Visual RAG'}
          </DialogTitle>
          <DialogDescription>
            {t.vrag?.index?.description ||
              'Select sources to extract and index images for multimodal search. Indexed images can be searched using visual queries.'}
          </DialogDescription>
        </DialogHeader>

        {sources.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm">
            {t.vrag?.index?.noSources || 'No sources available in this notebook.'}
          </div>
        ) : (
          <div className="space-y-3">
            {/* Select all */}
            <div className="flex items-center gap-2 pb-2 border-b">
              <Checkbox
                checked={selectedIds.size === sources.length && sources.length > 0}
                onCheckedChange={toggleSelectAll}
                id="select-all"
              />
              <label
                htmlFor="select-all"
                className="text-sm font-medium cursor-pointer"
              >
                {t.vrag?.index?.selectAll || 'Select all'} ({sources.length})
              </label>
            </div>

            {/* Source list */}
            <ScrollArea className="max-h-[300px]">
              <div className="space-y-2 pr-4">
                {sources.map((source) => {
                  const status = getStatus(source.id)
                  const isSelected = selectedIds.has(source.id)
                  const { icon: Icon, label } = getSourceType(source)

                  return (
                    <div
                      key={source.id}
                      className={`flex items-center gap-3 p-2 rounded-lg border transition-colors ${
                        isSelected
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:bg-muted/50'
                      }`}
                    >
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={() => toggleSource(source.id)}
                        id={`source-${source.id}`}
                        disabled={status === 'indexing' || status === 'rebuilding'}
                      />
                      <Icon className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                      <div className="flex-1 min-w-0">
                        <label
                          htmlFor={`source-${source.id}`}
                          className="text-sm font-medium cursor-pointer truncate block"
                        >
                          {source.title || (label === 'URL' ? source.asset?.url : source.id)}
                        </label>
                        <span className="text-xs text-muted-foreground">{label}</span>
                      </div>
                      {getStatusBadge(status)}
                    </div>
                  )
                })}
              </div>
            </ScrollArea>
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={handleRebuild}
            disabled={selectedIds.size === 0 || isIndexing}
            className="gap-1"
          >
            {isIndexing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {t.vrag?.index?.rebuild || 'Rebuild'}
          </Button>
          <Button
            onClick={handleIndex}
            disabled={selectedIds.size === 0 || isIndexing}
            className="gap-1"
          >
            {isIndexing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Zap className="h-4 w-4" />
            )}
            {t.vrag?.index?.indexSelected || 'Index Selected'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
