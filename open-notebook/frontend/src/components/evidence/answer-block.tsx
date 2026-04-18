import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Bot, Loader2, MessageSquareQuote, Sparkles } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatEvidenceConfidence } from '@/lib/project-evidence'
import { ProjectAskResponse } from '@/lib/types/api'

interface AnswerBlockProps {
  response?: ProjectAskResponse | null
  displayRunId?: string | null
  isRefreshing?: boolean
  disableSuggestedFollowups?: boolean
  onSuggestedFollowup?: (question: string) => void
}

export function AnswerBlock({
  response,
  displayRunId,
  isRefreshing = false,
  disableSuggestedFollowups = false,
  onSuggestedFollowup,
}: AnswerBlockProps) {
  if (!response) {
    return (
      <div className="rounded-md border border-dashed border-border/70 px-4 py-8 text-center text-sm text-muted-foreground">
        提出一个明确问题后，回答、置信度和追问建议会出现在这里。
      </div>
    )
  }

  return (
    <div className="space-y-4 rounded-md border border-border/70 bg-background px-4 py-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary" className="gap-1">
          <Bot className="h-3 w-3" />
          当前回答
        </Badge>
        <Badge variant="outline">{response.mode}</Badge>
        <Badge variant="outline">置信度 {formatEvidenceConfidence(response.confidence)}</Badge>
        <Badge variant="outline">
          {displayRunId ? `run ${displayRunId}` : 'run 待后续接入'}
        </Badge>
        {isRefreshing ? (
          <Badge variant="outline" className="gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            正在同步线程
          </Badge>
        ) : null}
      </div>

      <div className="prose prose-sm max-w-none break-words text-foreground dark:prose-invert">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{response.answer}</ReactMarkdown>
      </div>

      {response.suggested_followups.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Sparkles className="h-4 w-4 text-muted-foreground" />
            下一步可以继续问
          </div>

          <div className="flex flex-wrap gap-2">
            {response.suggested_followups.map((question) => (
              <Button
                key={question}
                type="button"
                variant="outline"
                size="sm"
                className="h-auto whitespace-normal px-3 py-2 text-left leading-5"
                disabled={disableSuggestedFollowups}
                onClick={() => onSuggestedFollowup?.(question)}
              >
                <MessageSquareQuote className="mr-1 h-3.5 w-3.5 flex-shrink-0" />
                <span className="break-words">{question}</span>
              </Button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
