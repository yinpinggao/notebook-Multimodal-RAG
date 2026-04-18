import { FileText, ImageIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { SourceJumpButton } from '@/components/evidence/source-jump-button'
import { EvidenceCardResponse } from '@/lib/types/api'

interface EvidenceCardProps {
  card: EvidenceCardResponse
}

function formatScore(score?: number | null) {
  if (typeof score !== 'number' || Number.isNaN(score)) {
    return '未评分'
  }

  return `${Math.round(Math.max(0, Math.min(1, score)) * 100)}%`
}

export function EvidenceCard({ card }: EvidenceCardProps) {
  return (
    <div className="space-y-3 rounded-md border border-border/70 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium">
            <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
            <span className="break-words">{card.source_name}</span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline">
              {card.page_no ? `第 ${card.page_no} 页` : '未提供页码'}
            </Badge>
            <Badge variant="secondary">{formatScore(card.score)}</Badge>
            {card.image_thumb ? (
              <Badge variant="outline" className="gap-1">
                <ImageIcon className="h-3 w-3" />
                页图摘要
              </Badge>
            ) : null}
          </div>
        </div>

        <SourceJumpButton
          sourceId={card.source_id}
          internalRef={card.internal_ref}
        />
      </div>

      <p className="break-words text-sm leading-6 text-foreground/90">{card.excerpt}</p>

      {card.relevance_reason ? (
        <div className="rounded-md bg-muted/50 px-3 py-2 text-xs leading-5 text-muted-foreground">
          {card.relevance_reason}
        </div>
      ) : null}

      <div className="space-y-1 text-xs text-muted-foreground">
        <div className="break-words">{card.citation_text}</div>
        <div className="break-all">内部定位：{card.internal_ref}</div>
      </div>
    </div>
  )
}
