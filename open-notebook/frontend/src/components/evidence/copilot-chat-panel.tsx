'use client'

import { useId, useMemo, useState } from 'react'
import { Bot, Loader2, Send, User } from 'lucide-react'

import { AnswerBlock } from '@/components/evidence/answer-block'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { PROJECT_ASK_MODE_OPTIONS } from '@/lib/project-evidence'
import {
  EvidenceThreadMessageResponse,
  ProjectAskMode,
  ProjectAskResponse,
} from '@/lib/types/api'

interface CopilotChatPanelProps {
  projectName?: string
  threadTitle?: string
  messages: EvidenceThreadMessageResponse[]
  response?: ProjectAskResponse | null
  replaceLatestAnswerInHistory?: boolean
  mode: ProjectAskMode
  isLoading?: boolean
  isRefreshing?: boolean
  isSubmitting?: boolean
  disableSubmission?: boolean
  pendingQuestion?: string | null
  displayRunId?: string | null
  errorMessage?: string | null
  onModeChange: (mode: ProjectAskMode) => void
  onSubmit: (question: string) => void
  onSuggestedFollowup?: (question: string) => void
}

function findLatestAiMessageIndex(messages: EvidenceThreadMessageResponse[]) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index]?.type === 'ai') {
      return index
    }
  }

  return -1
}

export function CopilotChatPanel({
  projectName,
  threadTitle,
  messages,
  response,
  replaceLatestAnswerInHistory = true,
  mode,
  isLoading = false,
  isRefreshing = false,
  isSubmitting = false,
  disableSubmission = false,
  pendingQuestion,
  displayRunId,
  errorMessage,
  onModeChange,
  onSubmit,
  onSuggestedFollowup,
}: CopilotChatPanelProps) {
  const inputId = useId()
  const [question, setQuestion] = useState('')

  const visibleMessages = useMemo(() => {
    if (!response || !replaceLatestAnswerInHistory) {
      return messages
    }

    const latestAiMessageIndex = findLatestAiMessageIndex(messages)
    if (latestAiMessageIndex < 0) {
      return messages
    }

    return messages.filter((_, index) => index !== latestAiMessageIndex)
  }, [messages, replaceLatestAnswerInHistory, response])

  const handleSubmit = () => {
    const normalized = question.trim()
    if (!normalized || isSubmitting || disableSubmission) {
      return
    }

    onSubmit(normalized)
    setQuestion('')
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const isMac =
      typeof navigator !== 'undefined' &&
      navigator.userAgent.toUpperCase().includes('MAC')

    if (
      event.key === 'Enter' &&
      (isMac ? event.metaKey : event.ctrlKey)
    ) {
      event.preventDefault()
      handleSubmit()
    }
  }

  const activeMode = PROJECT_ASK_MODE_OPTIONS.find((option) => option.value === mode)

  return (
    <div className="flex min-h-[38rem] flex-col overflow-hidden rounded-md border border-border/70 bg-background xl:h-[calc(100vh-18rem)]">
      <div className="space-y-3 border-b border-border/70 px-4 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="text-sm font-semibold">
              {threadTitle || '证据副驾'}
            </div>
            <div className="text-sm text-muted-foreground">
              {projectName
                ? `围绕 ${projectName} 持续提问、追问并沉淀证据。`
                : '围绕当前项目持续提问、追问并沉淀证据。'}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{messages.length} 条消息</Badge>
            <Badge variant="secondary">{activeMode?.label || '自动'}</Badge>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px]">
          <div className="space-y-1">
            <label htmlFor={inputId} className="text-xs font-medium text-muted-foreground">
              提问模式
            </label>
            <div className="text-xs leading-5 text-muted-foreground">
              {activeMode?.description}
            </div>
          </div>

          <div className="space-y-1">
            <Select
              value={mode}
              onValueChange={(value) => onModeChange(value as ProjectAskMode)}
            >
              <SelectTrigger id={`${inputId}-mode`}>
                <SelectValue placeholder="选择模式" />
              </SelectTrigger>
              <SelectContent>
                {PROJECT_ASK_MODE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-4 px-4 py-4">
          {errorMessage ? (
            <Alert variant="destructive">
              <AlertTitle>问答暂时失败</AlertTitle>
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          ) : null}

          {isLoading ? (
            <div className="flex min-h-48 items-center justify-center">
              <LoadingSpinner size="lg" />
            </div>
          ) : visibleMessages.length === 0 && !pendingQuestion && !response ? (
            <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-center text-sm text-muted-foreground">
              先问一个明确问题，比如“这个项目最关键的证据是什么？”或“这张图表说明了什么？”。
            </div>
          ) : null}

          {visibleMessages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${
                message.type === 'human' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.type === 'ai' ? (
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
              ) : null}

              <div
                className={`max-w-[85%] rounded-md px-4 py-3 text-sm leading-6 ${
                  message.type === 'human'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-foreground'
                }`}
              >
                <div className="break-words whitespace-pre-wrap">{message.content}</div>
              </div>

              {message.type === 'human' ? (
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary">
                  <User className="h-4 w-4 text-primary-foreground" />
                </div>
              ) : null}
            </div>
          ))}

          {pendingQuestion ? (
            <div className="flex justify-end gap-3">
              <div className="max-w-[85%] rounded-md bg-primary px-4 py-3 text-sm leading-6 text-primary-foreground">
                <div className="break-words whitespace-pre-wrap">{pendingQuestion}</div>
              </div>
              <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary">
                <User className="h-4 w-4 text-primary-foreground" />
              </div>
            </div>
          ) : null}

          {isSubmitting ? (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary/10">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div className="flex items-center gap-2 rounded-md bg-muted px-4 py-3 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                正在整理证据回答...
              </div>
            </div>
          ) : null}

          <AnswerBlock
            response={response}
            displayRunId={displayRunId}
            isRefreshing={Boolean(response) && isRefreshing}
            disableSuggestedFollowups={isSubmitting || disableSubmission}
            onSuggestedFollowup={onSuggestedFollowup}
          />
        </div>
      </ScrollArea>

      <div className="space-y-3 border-t border-border/70 px-4 py-4">
        <label htmlFor={inputId} className="text-xs font-medium text-muted-foreground">
          输入问题，使用 Ctrl+Enter / ⌘+Enter 发送
        </label>
        <Textarea
          id={inputId}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="例如：这个项目的主要创新点是什么？这张图表最支持哪个判断？"
          className="min-h-[116px] resize-none"
          disabled={isSubmitting || disableSubmission}
        />

        <div className="flex items-center justify-between gap-3">
          <div className="text-xs text-muted-foreground">
            当前会返回统一回答结构、证据卡和后续追问建议。
          </div>

          <Button
            type="button"
            className="gap-2"
            onClick={handleSubmit}
            disabled={!question.trim() || isSubmitting || disableSubmission}
          >
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            发送问题
          </Button>
        </div>
      </div>
    </div>
  )
}
