'use client'

import { useParams, useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { VRAGChatPanel } from '@/components/vrag/VRAGChatPanel'
import { IndexingDialog } from '@/components/vrag/IndexingDialog'
import { useVRAGChat } from '@/lib/hooks/useVRAGChat'
import { useNotebookSources } from '@/lib/hooks/use-sources'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useTranslation } from '@/lib/hooks/use-translation'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { BookOpen, DatabaseZap } from 'lucide-react'
import { useState, useMemo } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'

export default function VRAGPage() {
  const { t } = useTranslation()
  const params = useParams()
  const router = useRouter()

  // Get notebook ID from URL
  const notebookIdFromUrl = useMemo(
    () => (params?.id ? decodeURIComponent(params.id as string) : ''),
    [params?.id]
  )

  // Local state for notebook selection (when no URL param)
  const [selectedNotebookId, setSelectedNotebookId] = useState<string | null>(null)

  // Indexing dialog state
  const [indexingDialogOpen, setIndexingDialogOpen] = useState(false)

  // Determine active notebook ID - prefer URL param, fall back to selection
  const activeNotebookId = notebookIdFromUrl || selectedNotebookId || ''

  // Always fetch notebooks (needed for selector)
  const { data: notebooks = [], isLoading: notebooksLoading } = useNotebooks()

  // Fetch sources if we have a notebook
  const { sources, isLoading: sourcesLoading } = useNotebookSources(activeNotebookId)

  // Initialize VRAG chat if we have sources
  const vrag = useVRAGChat(activeNotebookId)

  // Extract source IDs
  const sourceIds = useMemo(
    () => sources.map(s => s.id),
    [sources]
  )

  // Loading state for notebooks
  if (notebooksLoading) {
    return (
      <AppShell>
        <div className="flex flex-col flex-1 items-center justify-center p-6">
          <LoadingSpinner size="lg" />
        </div>
      </AppShell>
    )
  }

  // No notebook selected - show selector
  if (!notebookIdFromUrl && !selectedNotebookId) {
    return (
      <AppShell>
        <NotebookSelector
          notebooks={notebooks}
          onSelect={(id) => {
            setSelectedNotebookId(id)
            router.push(`/vrag?id=${encodeURIComponent(id)}`)
          }}
        />
      </AppShell>
    )
  }

  // No notebooks exist
  if (!notebooks || notebooks.length === 0) {
    return (
      <AppShell>
        <div className="flex flex-col flex-1 items-center justify-center p-6">
          <BookOpen className="h-16 w-16 text-muted-foreground mb-4" />
          <h1 className="text-2xl font-bold mb-2">{t.vrag?.title || 'Visual RAG'}</h1>
          <p className="text-muted-foreground text-center max-w-md mb-4">
            {t.vrag?.selectNotebook || 'Please select a notebook to use Visual RAG'}
          </p>
          <p className="text-sm text-muted-foreground">
            You need to create a notebook first.
          </p>
        </div>
      </AppShell>
    )
  }

  // Loading sources
  if (sourcesLoading) {
    return (
      <AppShell>
        <div className="flex flex-col flex-1 items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      </AppShell>
    )
  }

  // Main VRAG chat interface
  return (
    <AppShell>
      <div className="flex flex-col flex-1 min-h-0 p-6">
        {/* Header with indexing button */}
        <div className="flex items-center justify-end mb-3 flex-shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIndexingDialogOpen(true)}
            className="gap-1.5 text-xs"
          >
            <DatabaseZap className="h-3.5 w-3.5" />
            {t.vrag?.index?.button || 'Index Sources'}
          </Button>
        </div>

        <VRAGChatPanel
          messages={vrag.messages}
          isStreaming={vrag.isStreaming}
          isComplete={vrag.isComplete}
          error={vrag.error}
          dag={vrag.dag}
          currentAnswer={vrag.currentAnswer}
          sessions={vrag.sessions}
          currentSession={vrag.currentSession}
          sessionId={vrag.sessionId}
          loadingSessions={vrag.loadingSessions}
          onSendMessage={(question, sIds, maxSteps, context) =>
            vrag.sendMessage(question, sIds || sourceIds, maxSteps, context)
          }
          onCancelStreaming={vrag.cancelStreaming}
          onSwitchSession={vrag.switchSession}
          onDeleteSession={vrag.deleteSession}
          onResetConversation={vrag.resetConversation}
          getEvidenceImages={vrag.getEvidenceImages}
          sourceIds={sourceIds}
        />

        <IndexingDialog
          open={indexingDialogOpen}
          onOpenChange={setIndexingDialogOpen}
          sources={sources}
        />
      </div>
    </AppShell>
  )
}

// Notebook selector component
function NotebookSelector({
  notebooks,
  onSelect,
}: {
  notebooks: Array<{ id: string; name: string }>
  onSelect: (notebookId: string) => void
}) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col flex-1 items-center justify-center p-6">
      <BookOpen className="h-16 w-16 text-muted-foreground mb-4" />
      <h1 className="text-2xl font-bold mb-2">{t.vrag?.title || 'Visual RAG'}</h1>
      <p className="text-muted-foreground text-center max-w-md mb-6">
        {t.vrag?.selectNotebook || 'Please select a notebook to use Visual RAG'}
      </p>
      <Select
        onValueChange={(value) => {
          if (value) {
            onSelect(value)
          }
        }}
      >
        <SelectTrigger className="w-[300px]">
          <SelectValue placeholder={t.vrag?.selectNotebook || 'Select a notebook...'} />
        </SelectTrigger>
        <SelectContent>
          {notebooks.map((notebook) => (
            <SelectItem key={notebook.id} value={notebook.id}>
              {notebook.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}