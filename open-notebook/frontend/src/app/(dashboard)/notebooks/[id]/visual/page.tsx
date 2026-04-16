'use client'

import { useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { DatabaseZap } from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Button } from '@/components/ui/button'
import { IndexingDialog } from '@/components/vrag/IndexingDialog'
import { VRAGChatPanel } from '@/components/vrag/VRAGChatPanel'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useNotebookSources } from '@/lib/hooks/use-sources'
import { useVRAGChat } from '@/lib/hooks/useVRAGChat'

export default function NotebookVisualRAGPage() {
  const { t } = useTranslation()
  const params = useParams()
  const notebookId = params?.id ? decodeURIComponent(params.id as string) : ''
  const [indexingDialogOpen, setIndexingDialogOpen] = useState(false)

  const { sources, isLoading: sourcesLoading } = useNotebookSources(notebookId)
  const vrag = useVRAGChat(notebookId)

  const sourceIds = useMemo(
    () => sources.map((source) => source.id),
    [sources]
  )

  if (sourcesLoading) {
    return (
      <AppShell>
        <div className="flex flex-col flex-1 items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="flex flex-col flex-1 min-h-0 p-6">
        <div className="flex items-center justify-between mb-3 flex-shrink-0">
          <div>
            <h1 className="text-xl font-semibold">{t.vrag?.title || 'Visual RAG'}</h1>
            <p className="text-sm text-muted-foreground">
              {t.vrag?.subtitle || 'Ask questions about visual content in your documents'}
            </p>
          </div>
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
          onSendMessage={(question, selectedSourceIds, maxSteps, context) =>
            vrag.sendMessage(question, selectedSourceIds || sourceIds, maxSteps, context)
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
