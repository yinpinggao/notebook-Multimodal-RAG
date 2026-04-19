'use client'

import { DragEvent, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  Bot,
  Loader2,
  MessageSquare,
  Pin,
  Plus,
  Settings2,
  User,
  X,
} from 'lucide-react'

import { AnswerBlock } from '@/components/evidence/answer-block'
import { EvidenceCard } from '@/components/evidence/evidence-card'
import { SaveMemoryDialog } from '@/components/harness/SaveMemoryDialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  DEFAULT_ASSISTANT_AGENT,
  groupAssistantContextItems,
  HARNESS_AGENT_TO_ASK_MODE,
  hasExplicitAssistantContext,
  mergeAssistantSearchParams,
} from '@/lib/assistant-workspace'
import {
  canContinueEvidenceThread,
  formatEvidenceConfidence,
} from '@/lib/project-evidence'
import { useProjectThreads, useProjectThread, useAskProject, useFollowupProjectThread } from '@/lib/hooks/use-project-evidence'
import { useProjectMemory, useCreateProjectMemory } from '@/lib/hooks/use-project-memory'
import { useNotes } from '@/lib/hooks/use-notes'
import { useNotebookSources } from '@/lib/hooks/use-sources'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useAssistantWorkspaceStore } from '@/lib/stores/assistant-workspace-store'
import {
  EvidenceThreadMessageResponse,
  MemoryStatus,
  MemoryType,
  ProjectAskResponse,
  SourceReferenceResponse,
} from '@/lib/types/api'
import { cn } from '@/lib/utils'

interface AgentPanelProps {
  projectId?: string
  className?: string
}

interface PendingMemoryDraft {
  text: string
  type: MemoryType
  status: MemoryStatus
  sourceRefs: SourceReferenceResponse[]
}

export function AgentPanel({ projectId, className }: AgentPanelProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { t } = useTranslation()
  const {
    currentAgent,
    currentThreadId,
    selectedContextItems,
    toggleContextItem,
    removeContextItem,
    clearContextItems,
  } = useAssistantWorkspaceStore()

  const {
    data: threads = [],
  } = useProjectThreads(projectId || '')
  const {
    data: threadDetail,
    isLoading: threadLoading,
    isFetching: threadRefreshing,
    error: threadError,
  } = useProjectThread(projectId || '', currentThreadId)
  const askProject = useAskProject(projectId || '')
  const followupProject = useFollowupProjectThread(projectId || '', currentThreadId)
  const createProjectMemory = useCreateProjectMemory(projectId || '')
  const { sources } = useNotebookSources(projectId || '')
  const { data: notes = [] } = useNotes(projectId)
  const { data: memories = [] } = useProjectMemory(projectId || '')

  const [question, setQuestion] = useState('')
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null)
  const [optimisticResponse, setOptimisticResponse] = useState<ProjectAskResponse | null>(null)
  const [memoryDraft, setMemoryDraft] = useState<PendingMemoryDraft | null>(null)

  const activeAgent = currentAgent || DEFAULT_ASSISTANT_AGENT
  const isSubmitting = askProject.isPending || followupProject.isPending
  const disableSubmission = Boolean(currentThreadId) && threadLoading
  const canContinueThread = canContinueEvidenceThread({
    threadId: currentThreadId,
    threadLoaded: Boolean(threadDetail),
    threadError: Boolean(threadError),
  })

  useEffect(() => {
    setOptimisticResponse(null)
  }, [currentThreadId])

  useEffect(() => {
    if (!optimisticResponse || !threadDetail?.latest_response) {
      return
    }

    if (threadDetail.latest_response.answer === optimisticResponse.answer) {
      setOptimisticResponse(null)
    }
  }, [optimisticResponse, threadDetail?.latest_response])

  const activeResponse = optimisticResponse ?? threadDetail?.latest_response ?? null
  const groupedContext = groupAssistantContextItems(selectedContextItems)
  const explicitContext = hasExplicitAssistantContext(selectedContextItems)
  const activeAgentLabel = useMemo(
    () => ({
      research: t.assistant.researchAgent,
      retrieval: t.assistant.retrievalAgent,
      visual: t.assistant.visualAgent,
      synthesis: t.assistant.synthesisAgent,
    })[activeAgent],
    [activeAgent, t]
  )

  const handleSubmit = async (presetQuestion?: string) => {
    const nextQuestion = (presetQuestion ?? question).trim()
    if (!projectId || !nextQuestion || isSubmitting || disableSubmission) {
      return
    }

    const payload = {
      question: nextQuestion,
      mode: HARNESS_AGENT_TO_ASK_MODE[activeAgent],
      agent: activeAgent,
      source_ids: explicitContext ? groupedContext.sourceIds : undefined,
      note_ids: explicitContext ? groupedContext.noteIds : undefined,
      memory_ids: explicitContext ? groupedContext.memoryIds : undefined,
    }

    setPendingQuestion(nextQuestion)

    try {
      const response = canContinueThread
        ? await followupProject.mutateAsync(payload)
        : await askProject.mutateAsync(payload)

      setOptimisticResponse(response)
      setQuestion('')

      router.replace(
        mergeAssistantSearchParams(searchParams, {
          threadId: response.thread_id || null,
        }),
        { scroll: false }
      )
    } finally {
      setPendingQuestion(null)
    }
  }

  const latestAiMessageId = useMemo(() => {
    const messages = threadDetail?.messages || []
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index]?.type === 'ai') {
        return messages[index]?.id
      }
    }
    return null
  }, [threadDetail?.messages])

  const visibleMessages = useMemo(() => {
    const messages = threadDetail?.messages || []
    if (!activeResponse) {
      return messages
    }

    const latestAiIndex = messages.findLastIndex((message) => message.type === 'ai')
    if (latestAiIndex < 0) {
      return messages
    }

    const latestAiMessage = messages[latestAiIndex]
    if (latestAiMessage.content.trim() !== activeResponse.answer.trim()) {
      return messages
    }

    return messages.filter((_, index) => index !== latestAiIndex)
  }, [activeResponse, threadDetail?.messages])

  const openSaveDialog = (params: {
    text: string
    sourceRefs?: SourceReferenceResponse[]
    type?: MemoryType
    status?: MemoryStatus
  }) => {
    setMemoryDraft({
      text: params.text,
      sourceRefs: params.sourceRefs || [],
      type: params.type || 'fact',
      status: params.status || 'draft',
    })
  }

  const handleSaveMemory = async (payload: PendingMemoryDraft) => {
    if (!projectId) {
      return
    }

    await createProjectMemory.mutateAsync({
      text: payload.text,
      type: payload.type,
      status: payload.status,
      scope: 'project',
      source_refs: payload.sourceRefs,
    })
    setMemoryDraft(null)
  }

  const handleDropContext = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    const raw = event.dataTransfer.getData('application/x-assistant-context')
    if (!raw) {
      return
    }

    const item = JSON.parse(raw)
    if (item?.id && item?.type && item?.label) {
      toggleContextItem(item)
    }
  }

  const renderMessage = (message: EvidenceThreadMessageResponse) => {
    const isAi = message.type === 'ai'
    const sourceRefs =
      isAi && message.id === latestAiMessageId && activeResponse
        ? activeResponse.evidence_cards.map((card) => ({
            source_id: card.source_id,
            source_name: card.source_name,
            page_no: card.page_no,
            internal_ref: card.internal_ref,
            citation_text: card.citation_text,
          }))
        : []

    return (
      <div
        key={message.id}
        className={cn(
          'flex gap-3',
          isAi ? 'justify-start' : 'justify-end'
        )}
      >
        {isAi ? (
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary/10">
            <Bot className="h-4 w-4 text-primary" />
          </div>
        ) : null}

        <div
          className={cn(
            'max-w-[85%] space-y-2 rounded-md px-4 py-3 text-sm leading-6',
            isAi ? 'bg-muted text-foreground' : 'bg-primary text-primary-foreground'
          )}
        >
          <div className="break-words whitespace-pre-wrap">{message.content}</div>
          <div className={cn('flex justify-end', isAi ? 'text-foreground' : 'text-primary-foreground')}>
            <Button
              type="button"
              size="sm"
              variant={isAi ? 'outline' : 'secondary'}
              className="h-7"
              onClick={() =>
                openSaveDialog({
                  text: message.content,
                  sourceRefs,
                  type: 'fact',
                  status: 'draft',
                })
              }
            >
              <Pin className="mr-2 h-3.5 w-3.5" />
              {t.assistant.saveToMemory}
            </Button>
          </div>
        </div>

        {!isAi ? (
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary">
            <User className="h-4 w-4 text-primary-foreground" />
          </div>
        ) : null}
      </div>
    )
  }

  return (
    <>
      <section className={cn('flex h-full min-h-0 flex-col bg-background', className)}>
        <div className="space-y-4 border-b border-border/70 px-4 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold">{t.assistant.workspace}</div>
              <div className="text-xs text-muted-foreground">
                {t.assistant.agentHint}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  router.replace(
                    mergeAssistantSearchParams(searchParams, {
                      threadId: null,
                    }),
                    { scroll: false }
                  )
                }
              >
                <Plus className="mr-2 h-4 w-4" />
                {t.assistant.newThread}
              </Button>

              <Popover>
                <PopoverTrigger asChild>
                  <Button type="button" variant="outline" size="sm">
                    <Settings2 className="mr-2 h-4 w-4" />
                    {t.assistant.advancedSettings}
                  </Button>
                </PopoverTrigger>
                <PopoverContent align="end" className="w-80 space-y-3">
                  <div className="text-sm font-medium">{t.assistant.advancedSettings}</div>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <div>{t.assistant.currentAgentLabel.replace('{agent}', activeAgentLabel)}</div>
                    <div>{t.assistant.currentModeLabel.replace('{mode}', HARNESS_AGENT_TO_ASK_MODE[activeAgent])}</div>
                    <div>{t.assistant.currentContextLabel.replace('{count}', String(selectedContextItems.length))}</div>
                    <div>{t.assistant.currentThreadLabel.replace('{thread}', currentThreadId || t.assistant.noneSelected)}</div>
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px]">
            <Select
              value={currentThreadId || '__new__'}
              onValueChange={(value) =>
                router.replace(
                  mergeAssistantSearchParams(searchParams, {
                    threadId: value === '__new__' ? null : value,
                  }),
                  { scroll: false }
                )
              }
            >
              <SelectTrigger>
                <SelectValue placeholder={t.assistant.selectThread} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__new__">{t.assistant.newThread}</SelectItem>
                {threads.map((thread) => (
                  <SelectItem key={thread.id} value={thread.id}>
                    {thread.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex items-center gap-2 rounded-md border border-border/70 px-3 py-2 text-sm text-muted-foreground">
              <MessageSquare className="h-4 w-4" />
              {activeResponse
                ? t.assistant.confidenceLabel.replace(
                    '{confidence}',
                    formatEvidenceConfidence(activeResponse.confidence)
                  )
                : t.assistant.waitingForAnswer}
            </div>
          </div>
        </div>

      <ScrollArea
        className="min-h-0 flex-1 overflow-hidden"
        data-testid="agent-message-scroll"
      >
        <div className="space-y-4 px-4 py-4 pb-8">
            {!projectId ? (
              <div className="rounded-md border border-dashed border-border/70 px-4 py-10 text-sm text-muted-foreground">
                {t.assistant.selectProjectHint}
              </div>
            ) : threadLoading ? (
              <div className="flex min-h-40 items-center justify-center text-sm text-muted-foreground">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t.common.loading}
              </div>
            ) : (
              <>
                {visibleMessages.map(renderMessage)}

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
                      {t.assistant.generatingAnswer}
                    </div>
                  </div>
                ) : null}

                <AnswerBlock
                  response={activeResponse}
                  displayRunId={activeResponse?.run_id}
                  isRefreshing={Boolean(activeResponse) && threadRefreshing}
                  disableSuggestedFollowups={isSubmitting || disableSubmission}
                  onSuggestedFollowup={(followup) => {
                    void handleSubmit(followup)
                  }}
                />

                {activeResponse?.evidence_cards?.length ? (
                  <div className="space-y-3">
                    <div className="text-sm font-semibold">{t.assistant.evidenceHeading}</div>
                    <div className="space-y-3">
                      {activeResponse.evidence_cards.map((card) => (
                        <EvidenceCard key={`${card.source_id}:${card.internal_ref}`} card={card} />
                      ))}
                    </div>
                    <div className="flex justify-end">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          openSaveDialog({
                            text: activeResponse.answer,
                            sourceRefs: activeResponse.evidence_cards.map((card) => ({
                              source_id: card.source_id,
                              source_name: card.source_name,
                              page_no: card.page_no,
                              internal_ref: card.internal_ref,
                              citation_text: card.citation_text,
                            })),
                          })
                        }
                      >
                        <Pin className="mr-2 h-4 w-4" />
                        {t.assistant.saveAnswerToMemory}
                      </Button>
                    </div>
                  </div>
                ) : null}
              </>
            )}
          </div>
        </ScrollArea>

        <div
          className="space-y-3 border-t border-border/70 px-4 py-4"
          onDragOver={(event) => event.preventDefault()}
          onDrop={handleDropContext}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs font-medium text-muted-foreground">
              {t.assistant.context}
            </div>
            <div className="flex items-center gap-2">
              <Popover>
                <PopoverTrigger asChild>
                  <Button type="button" variant="outline" size="sm">
                    {t.assistant.contextSelector}
                  </Button>
                </PopoverTrigger>
                <PopoverContent align="end" className="w-96">
                  <div className="space-y-4">
                    <div className="text-sm font-medium">{t.assistant.contextSelector}</div>

                    <div className="space-y-2">
                      <div className="text-xs font-medium text-muted-foreground">
                        {t.navigation.sources}
                      </div>
                      <div className="space-y-2">
                        {sources.slice(0, 8).map((source) => {
                          const checked = selectedContextItems.some(
                            (item) => item.type === 'source' && item.id === source.id
                          )
                          return (
                            <label
                              key={source.id}
                              className="flex cursor-pointer items-center gap-3 rounded-md border border-border/70 px-3 py-2 text-sm"
                            >
                              <Checkbox
                                checked={checked}
                                onCheckedChange={() =>
                                  toggleContextItem({
                                    id: source.id,
                                    type: 'source',
                                    label: source.title || source.id,
                                    contextMode: source.insights_count > 0 ? 'insights' : 'full',
                                  })
                                }
                              />
                              <span className="min-w-0 truncate">{source.title || source.id}</span>
                            </label>
                          )
                        })}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="text-xs font-medium text-muted-foreground">
                        {t.common.notes}
                      </div>
                      <div className="space-y-2">
                        {notes.slice(0, 8).map((note) => {
                          const checked = selectedContextItems.some(
                            (item) => item.type === 'note' && item.id === note.id
                          )
                          return (
                            <label
                              key={note.id}
                              className="flex cursor-pointer items-center gap-3 rounded-md border border-border/70 px-3 py-2 text-sm"
                            >
                              <Checkbox
                                checked={checked}
                                onCheckedChange={() =>
                                  toggleContextItem({
                                    id: note.id,
                                    type: 'note',
                                    label: note.title || note.id,
                                    contextMode: 'full',
                                  })
                                }
                              />
                              <span className="min-w-0 truncate">{note.title || note.id}</span>
                            </label>
                          )
                        })}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="text-xs font-medium text-muted-foreground">
                        {t.assistant.memoryManager}
                      </div>
                      <div className="space-y-2">
                        {memories.slice(0, 8).map((memory) => {
                          const checked = selectedContextItems.some(
                            (item) => item.type === 'memory' && item.id === memory.id
                          )
                          return (
                            <label
                              key={memory.id}
                              className="flex cursor-pointer items-center gap-3 rounded-md border border-border/70 px-3 py-2 text-sm"
                            >
                              <Checkbox
                                checked={checked}
                                onCheckedChange={() =>
                                  toggleContextItem({
                                    id: memory.id,
                                    type: 'memory',
                                    label: memory.text,
                                    contextMode: 'full',
                                  })
                                }
                              />
                              <span className="min-w-0 truncate">{memory.text}</span>
                            </label>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                </PopoverContent>
              </Popover>

              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={clearContextItems}
                disabled={selectedContextItems.length === 0}
              >
                {t.assistant.clearContext}
              </Button>
            </div>
          </div>

          <div className="flex min-h-[48px] flex-wrap gap-2 rounded-md border border-dashed border-border/70 px-3 py-3">
            {selectedContextItems.length === 0 ? (
              <div className="text-sm text-muted-foreground">
                {t.assistant.dropContextHint}
              </div>
            ) : (
              selectedContextItems.map((item) => (
                <div
                  key={`${item.type}:${item.id}`}
                  className="inline-flex items-center gap-2 rounded-md border border-border/70 bg-muted/30 px-3 py-1.5 text-sm"
                >
                  <span className="max-w-[220px] truncate">{item.label}</span>
                  <button
                    type="button"
                    aria-label={t.common.remove}
                    onClick={() => removeContextItem(item.type, item.id)}
                  >
                    <X className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                </div>
              ))
            )}
          </div>

          <div className="grid gap-3">
            <Textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={t.assistant.askPlaceholder}
              className="min-h-[110px] resize-none"
              onKeyDown={(event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
                  event.preventDefault()
                  void handleSubmit()
                }
              }}
            />

            <div className="flex items-center justify-between gap-3">
              <div className="text-xs text-muted-foreground">
                {t.assistant.contextCountLabel.replace(
                  '{count}',
                  String(selectedContextItems.length)
                )}
              </div>
              <Button
                type="button"
                onClick={() => {
                  void handleSubmit()
                }}
                disabled={!projectId || !question.trim() || isSubmitting || disableSubmission}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t.assistant.generatingAnswer}
                  </>
                ) : (
                  t.assistant.sendToAgent
                )}
              </Button>
            </div>
          </div>
        </div>
      </section>

      <SaveMemoryDialog
        open={Boolean(memoryDraft)}
        isSaving={createProjectMemory.isPending}
        defaultText={memoryDraft?.text || ''}
        defaultType={memoryDraft?.type}
        defaultStatus={memoryDraft?.status}
        sourceRefs={memoryDraft?.sourceRefs || []}
        onOpenChange={(open) => {
          if (!open) {
            setMemoryDraft(null)
          }
        }}
        onSave={(payload) => {
          void handleSaveMemory({
            text: payload.text,
            type: payload.type,
            status: payload.status,
            sourceRefs: payload.sourceRefs,
          })
        }}
      />
    </>
  )
}
