import { Activity, FileSearch, Files, Sparkles } from 'lucide-react'

import { EvidenceCard } from '@/components/evidence/evidence-card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { formatEvidenceConfidence } from '@/lib/project-evidence'
import { ProjectAskResponse } from '@/lib/types/api'

interface EvidenceSidePanelProps {
  response?: ProjectAskResponse | null
  displayRunId?: string | null
}

export function EvidenceSidePanel({
  response,
  displayRunId,
}: EvidenceSidePanelProps) {
  return (
    <div className="flex min-h-[30rem] flex-col overflow-hidden rounded-md border border-border/70 bg-background xl:h-[calc(100vh-18rem)]">
      <div className="space-y-3 border-b border-border/70 px-4 py-4">
        <div className="flex items-center gap-2">
          <Files className="h-4 w-4 text-muted-foreground" />
          <div className="text-sm font-semibold">证据与运行摘要</div>
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
          <div className="rounded-md border border-border/70 px-3 py-3">
            <div className="text-xs text-muted-foreground">run_id</div>
            <div className="mt-1 break-all text-sm font-medium">
              {displayRunId || '待后续 runs 接入'}
            </div>
          </div>

          <div className="rounded-md border border-border/70 px-3 py-3">
            <div className="text-xs text-muted-foreground">回答模式</div>
            <div className="mt-1 flex items-center gap-2">
              <Badge variant="outline">{response?.mode || '待生成'}</Badge>
              <Badge variant="secondary">
                置信度 {formatEvidenceConfidence(response?.confidence)}
              </Badge>
            </div>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
          <div className="rounded-md border border-border/70 px-3 py-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Activity className="h-3.5 w-3.5" />
              Evidence Cards
            </div>
            <div className="mt-1 text-sm font-medium">
              {response?.evidence_cards.length || 0} 条
            </div>
          </div>

          <div className="rounded-md border border-border/70 px-3 py-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5" />
              Memory Updates
            </div>
            <div className="mt-1 text-sm font-medium">
              {response?.memory_updates.length || 0} 条
            </div>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-4 px-4 py-4">
          {response?.evidence_cards.length ? (
            response.evidence_cards.map((card) => (
              <EvidenceCard
                key={card.id || `${card.source_id}:${card.internal_ref}`}
                card={card}
              />
            ))
          ) : (
            <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-center text-sm text-muted-foreground">
              <FileSearch className="mx-auto mb-3 h-10 w-10 opacity-50" />
              当前还没有可展示的证据卡。完成一次问答后，来源定位和摘要会出现在这里。
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
