"use client";

import { useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AlertCircle, DatabaseZap } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { IndexingDialog } from "@/components/vrag/IndexingDialog";
import { VRAGChatPanel } from "@/components/vrag/VRAGChatPanel";
import { useTranslation } from "@/lib/hooks/use-translation";
import { useNotebookSources, useSources } from "@/lib/hooks/use-sources";
import { useVRAGChat } from "@/lib/hooks/useVRAGChat";

export default function NotebookVisualRAGPage() {
  const { t } = useTranslation();
  const params = useParams();
  const notebookId = params?.id ? decodeURIComponent(params.id as string) : "";
  const [indexingDialogOpen, setIndexingDialogOpen] = useState(false);

  const { sources, isLoading: sourcesLoading } = useNotebookSources(notebookId);
  const { data: workspaceSources = [], isLoading: workspaceSourcesLoading } =
    useSources();
  const vrag = useVRAGChat(notebookId);

  const fallbackSources = useMemo(
    () =>
      workspaceSources.filter(
        (source) =>
          source.visual_index_status === "completed" &&
          (source.visual_asset_count || 0) > 0,
      ),
    [workspaceSources],
  );
  const effectiveSources = sources.length > 0 ? sources : fallbackSources;
  const indexingSources = sources.length > 0 ? sources : workspaceSources;
  const sourceIds = useMemo(
    () => effectiveSources.map((source) => source.id),
    [effectiveSources],
  );
  const usingWorkspaceFallback =
    sources.length === 0 && effectiveSources.length > 0;
  const noVisualSources = sourceIds.length === 0;

  if (sourcesLoading || (sources.length === 0 && workspaceSourcesLoading)) {
    return (
      <AppShell>
        <div className="flex flex-col flex-1 items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex flex-col flex-1 min-h-0 overflow-hidden p-6">
        <div className="flex items-center justify-between mb-3 flex-shrink-0">
          <div>
            <h1 className="text-xl font-semibold">
              {t.vrag?.title || "Visual RAG"}
            </h1>
            <p className="text-sm text-muted-foreground">
              {t.vrag?.subtitle ||
                "Ask questions about visual content in your documents"}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIndexingDialogOpen(true)}
            className="gap-1.5 text-xs"
          >
            <DatabaseZap className="h-3.5 w-3.5" />
            {t.vrag?.index?.button || "Index Sources"}
          </Button>
        </div>

        {usingWorkspaceFallback && (
          <Alert className="mb-3 border-amber-500/30 bg-amber-50/70 dark:bg-amber-950/20">
            <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <AlertTitle>
              {t.vrag?.workspaceFallbackTitle || "Using workspace sources"}
            </AlertTitle>
            <AlertDescription>
              {t.vrag?.workspaceFallbackDescription ||
                "This notebook has no linked sources. Visual RAG is temporarily using indexed sources from the workspace."}
            </AlertDescription>
          </Alert>
        )}

        {noVisualSources && (
          <Alert className="mb-3">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>
              {t.vrag?.noVisualSourcesTitle || "No visual sources available"}
            </AlertTitle>
            <AlertDescription>
              {t.vrag?.noVisualSourcesDescription ||
                "Add or link a PDF source, then build its visual index before starting a Visual RAG chat."}
            </AlertDescription>
          </Alert>
        )}

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
            vrag.sendMessage(
              question,
              selectedSourceIds || sourceIds,
              maxSteps,
              context,
            )
          }
          onCancelStreaming={vrag.cancelStreaming}
          onSwitchSession={vrag.switchSession}
          onDeleteSession={vrag.deleteSession}
          onResetConversation={vrag.resetConversation}
          getEvidenceImages={vrag.getEvidenceImages}
          sourceIds={sourceIds}
          inputDisabledReason={
            noVisualSources
              ? t.vrag?.inputDisabledNoSources ||
                "No indexed visual sources are available for this chat."
              : undefined
          }
        />

        <IndexingDialog
          open={indexingDialogOpen}
          onOpenChange={setIndexingDialogOpen}
          sources={indexingSources}
        />
      </div>
    </AppShell>
  );
}
