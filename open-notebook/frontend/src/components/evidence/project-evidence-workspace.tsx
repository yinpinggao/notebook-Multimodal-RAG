'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle, Clock3, MessageSquareQuote, Plus } from 'lucide-react'

import { CopilotChatPanel } from '@/components/evidence/copilot-chat-panel'
import { EvidenceSidePanel } from '@/components/evidence/evidence-side-panel'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import {
  CollapsibleRail,
  PageHeader,
} from '@/components/projects/page-templates'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  useAskProject,
  useFollowupProjectThread,
  useProjectThread,
  useProjectThreads,
} from '@/lib/hooks/use-project-evidence'
import { useProjectOverview } from '@/lib/hooks/use-projects'
import {
  buildProjectEvidencePath,
  canContinueEvidenceThread,
  formatEvidenceConfidence,
} from '@/lib/project-evidence'
import { buildProjectPath } from '@/lib/project-paths'
import { formatProjectTimestamp } from '@/lib/project-workspace'
import { useAssistantWorkspaceStore } from '@/lib/stores/assistant-workspace-store'
import { ProjectAskMode, ProjectAskResponse } from '@/lib/types/api'
import { cn } from '@/lib/utils'
import { formatApiError } from '@/lib/utils/error-handler'

interface ProjectEvidenceWorkspaceProps {
  projectId: string
  initialThreadId?: string
}

const DEFAULT_RECOMMENDED_QUESTIONS = [
  '这个项目目前最扎实的证据链是什么？',
  '如果我要先看一页最关键的资料，应该从哪里开始？',
  '当前证据还缺哪一块，导致结论不够稳？',
]

function buildRunStorageKey(projectId: string, threadId: string) {
  return `project-evidence-run:${projectId}:${threadId}`
}

export function ProjectEvidenceWorkspace({
  projectId,
  initialThreadId,
}: ProjectEvidenceWorkspaceProps) {
  const router = useRouter()
  const { setLastEvidenceThreadId, setLastProjectId } = useAssistantWorkspaceStore()
  const [mode, setMode] = useState<ProjectAskMode>('auto')
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null)
  const [optimisticResponse, setOptimisticResponse] = useState<ProjectAskResponse | null>(null)
  const [storedRunId, setStoredRunId] = useState<string | null>(null)
  const [threadsOpen, setThreadsOpen] = useState(true)
  const [evidenceOpen, setEvidenceOpen] = useState(true)

  const {
    data: overviewResponse,
    error: overviewError,
  } = useProjectOverview(projectId)
  const {
    data: threads = [],
    isLoading: threadsLoading,
    error: threadsError,
  } = useProjectThreads(projectId)
  const {
    data: threadDetail,
    isLoading: threadLoading,
    isFetching: threadFetching,
    error: threadError,
  } = useProjectThread(projectId, initialThreadId)

  const askProject = useAskProject(projectId)
  const followupProject = useFollowupProjectThread(projectId, initialThreadId)
  const isSubmitting = askProject.isPending || followupProject.isPending

  useEffect(() => {
    setLastProjectId(projectId)
  }, [projectId, setLastProjectId])

  useEffect(() => {
    if (initialThreadId) {
      setLastEvidenceThreadId(initialThreadId)
    }
  }, [initialThreadId, setLastEvidenceThreadId])

  useEffect(() => {
    setOptimisticResponse(null)
  }, [initialThreadId])

  useEffect(() => {
    if (typeof window === 'undefined' || !initialThreadId) {
      setStoredRunId(null)
      return
    }

    setStoredRunId(sessionStorage.getItem(buildRunStorageKey(projectId, initialThreadId)))
  }, [initialThreadId, projectId])

  useEffect(() => {
    if (!optimisticResponse || !threadDetail?.latest_response) {
      return
    }

    if (threadDetail.latest_response.answer === optimisticResponse.answer) {
      setOptimisticResponse(null)
    }
  }, [optimisticResponse, threadDetail?.latest_response])

  const activeResponse = optimisticResponse ?? threadDetail?.latest_response ?? null
  const displayRunId = activeResponse?.run_id || storedRunId
  const canContinueThread = canContinueEvidenceThread({
    threadId: initialThreadId,
    threadLoaded: Boolean(threadDetail),
    threadError: Boolean(threadError),
  })
  const disableSubmission = Boolean(initialThreadId) && threadLoading
  const replaceLatestAnswerInHistory =
    !optimisticResponse ||
    optimisticResponse.answer === threadDetail?.latest_response?.answer
  const recommendedQuestions =
    overviewResponse?.recommended_questions?.length
      ? overviewResponse.recommended_questions
      : DEFAULT_RECOMMENDED_QUESTIONS
  const projectName = overviewResponse?.project.name || '项目空间'

  const submitError = followupProject.error || askProject.error
  const threadErrorMessage =
    initialThreadId && threadError ? formatApiError(threadError) : null
  const mutationErrorMessage = submitError ? formatApiError(submitError) : null

  const persistRunId = (threadId?: string | null, runId?: string | null) => {
    if (typeof window === 'undefined' || !threadId || !runId) {
      return
    }

    sessionStorage.setItem(buildRunStorageKey(projectId, threadId), runId)
    if (threadId === initialThreadId) {
      setStoredRunId(runId)
    }
  }

  const handleSubmitQuestion = async (question: string) => {
    if (isSubmitting || disableSubmission) {
      return
    }

    setPendingQuestion(question)

    try {
      if (canContinueThread) {
        const response = await followupProject.mutateAsync({
          question,
          mode,
        })
        setOptimisticResponse(response)
        persistRunId(response.thread_id, response.run_id)
        if (response.thread_id) {
          setLastEvidenceThreadId(response.thread_id)
        }

        if (response.thread_id && response.thread_id !== initialThreadId) {
          router.push(buildProjectEvidencePath(projectId, response.thread_id))
        }
      } else {
        const response = await askProject.mutateAsync({
          question,
          mode,
        })
        persistRunId(response.thread_id, response.run_id)
        if (response.thread_id) {
          setLastEvidenceThreadId(response.thread_id)
        }

        if (response.thread_id) {
          router.push(buildProjectEvidencePath(projectId, response.thread_id))
        }
      }
    } catch {
      // Errors are rendered inline by the panel.
    } finally {
      setPendingQuestion(null)
    }
  }

  const threadItems = useMemo(() => threads, [threads])

  const threadsPanel = (
    <div className="rounded-md border border-border/70 bg-background">
      <div className="flex items-center justify-between gap-3 border-b border-border/70 px-4 py-4">
        <div>
          <div className="text-sm font-semibold">线程</div>
          <div className="text-xs text-muted-foreground">
            在同一项目里连续追问，别把上下文切断。
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          className="gap-1"
          onClick={() => router.push(buildProjectEvidencePath(projectId))}
        >
          <Plus className="h-3.5 w-3.5" />
          新提问
        </Button>
      </div>

      <ScrollArea className="h-[18rem] lg:h-[24rem]">
        <div className="space-y-3 px-4 py-4">
          {threadsError ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>线程列表暂时加载失败</AlertTitle>
              <AlertDescription>{formatApiError(threadsError)}</AlertDescription>
            </Alert>
          ) : threadsLoading ? (
            <div className="flex min-h-40 items-center justify-center">
              <LoadingSpinner size="sm" />
            </div>
          ) : threadItems.length === 0 ? (
            <div className="rounded-md border border-dashed border-border/70 px-4 py-8 text-sm text-muted-foreground">
              还没有线程。从推荐问题开始，或直接提出第一个问题。
            </div>
          ) : (
            threadItems.map((thread) => {
              const isActive = thread.id === initialThreadId

              return (
                <button
                  key={thread.id}
                  type="button"
                  className={cn(
                    'w-full rounded-md border px-3 py-3 text-left transition-colors',
                    isActive
                      ? 'border-foreground bg-muted/20'
                      : 'border-border/70 hover:border-foreground/20 hover:bg-muted/20'
                  )}
                  onClick={() => router.push(buildProjectEvidencePath(projectId, thread.id))}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="break-words text-sm font-medium">{thread.title}</div>
                      <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock3 className="h-3.5 w-3.5" />
                        {formatProjectTimestamp(thread.updated_at)}
                      </div>
                    </div>
                    <Badge variant={isActive ? 'default' : 'outline'}>{thread.message_count}</Badge>
                  </div>

                  {thread.last_question ? (
                    <div className="mt-3 line-clamp-2 break-words text-xs leading-5 text-muted-foreground">
                      {thread.last_question}
                    </div>
                  ) : null}
                </button>
              )
            })
          )}
        </div>
      </ScrollArea>
    </div>
  )

  const recommendedPanel = (
    <div className="rounded-md border border-border/70 bg-background">
      <div className="border-b border-border/70 px-4 py-4">
        <div className="flex items-center gap-2">
          <MessageSquareQuote className="h-4 w-4 text-muted-foreground" />
          <div className="text-sm font-semibold">推荐问题</div>
        </div>
        <div className="mt-1 text-xs leading-5 text-muted-foreground">
          先用这些问题把主线跑通，再继续追问细节。
        </div>
      </div>

      <div className="space-y-3 px-4 py-4">
        {overviewError ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>推荐问题暂时不可用</AlertTitle>
            <AlertDescription>{formatApiError(overviewError)}</AlertDescription>
          </Alert>
        ) : (
          recommendedQuestions.map((question) => (
            <button
              key={question}
              type="button"
              className="w-full rounded-md border border-border/70 px-3 py-3 text-left text-sm leading-6 transition-colors hover:border-foreground/20 hover:bg-muted/20 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting || disableSubmission}
              onClick={() => handleSubmitQuestion(question)}
            >
              {question}
            </button>
          ))
        )}
      </div>
    </div>
  )

  const summaryPanel = (
    <div className="rounded-md border border-border/70 bg-background px-4 py-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">{projectName}</Badge>
        <Badge variant="secondary">
          当前回答 {formatEvidenceConfidence(activeResponse?.confidence)}
        </Badge>
        {initialThreadId ? <Badge variant="outline">线程已连接</Badge> : null}
      </div>
      <div className="mt-2 text-sm leading-6 text-muted-foreground">
        右侧会跟着当前回答显示证据卡和运行摘要。宽屏三栏，中屏折叠，窄屏堆叠。
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button asChild variant="outline" size="sm">
          <Link href={buildProjectPath({ projectId, section: 'overview' })}>返回项目总览</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href={buildProjectPath({ projectId, section: 'runs' })}>查看运行轨迹</Link>
        </Button>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={<Badge variant="outline">Evidence Workspace</Badge>}
        title="证据工作台"
        description="把线程、推荐问题、回答和证据放进同一条工作流里。"
      />

      <div className="hidden min-[1440px]:grid min-[1440px]:grid-cols-[minmax(260px,0.85fr)_minmax(0,1.55fr)_minmax(300px,1fr)] min-[1440px]:gap-4">
        <aside className="space-y-4">
          {threadsPanel}
          {recommendedPanel}
        </aside>

        <div className="space-y-4">
          {threadErrorMessage ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>线程暂时打不开</AlertTitle>
              <AlertDescription className="space-y-3">
                <p>{threadErrorMessage}</p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => router.push(buildProjectEvidencePath(projectId))}
                >
                  返回证据工作台入口
                </Button>
              </AlertDescription>
            </Alert>
          ) : null}

          <CopilotChatPanel
            projectName={projectName}
            threadTitle={threadDetail?.title || (initialThreadId ? '正在载入线程...' : '证据副驾')}
            messages={threadDetail?.messages || []}
            response={activeResponse}
            replaceLatestAnswerInHistory={replaceLatestAnswerInHistory}
            mode={mode}
            isLoading={Boolean(initialThreadId) && threadLoading}
            isSubmitting={isSubmitting}
            disableSubmission={disableSubmission}
            pendingQuestion={pendingQuestion}
            displayRunId={displayRunId}
            errorMessage={mutationErrorMessage}
            onModeChange={setMode}
            onSubmit={handleSubmitQuestion}
            onSuggestedFollowup={handleSubmitQuestion}
            isRefreshing={Boolean(initialThreadId) && threadFetching && !threadLoading}
          />
        </div>

        <div className="space-y-4">
          {summaryPanel}
          <EvidenceSidePanel response={activeResponse} displayRunId={displayRunId} />
        </div>
      </div>

      <div className="hidden gap-4 lg:grid min-[1440px]:hidden lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)]">
        <div className="space-y-4">
          {threadErrorMessage ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>线程暂时打不开</AlertTitle>
              <AlertDescription className="space-y-3">
                <p>{threadErrorMessage}</p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => router.push(buildProjectEvidencePath(projectId))}
                >
                  返回证据工作台入口
                </Button>
              </AlertDescription>
            </Alert>
          ) : null}

          <CopilotChatPanel
            projectName={projectName}
            threadTitle={threadDetail?.title || (initialThreadId ? '正在载入线程...' : '证据副驾')}
            messages={threadDetail?.messages || []}
            response={activeResponse}
            replaceLatestAnswerInHistory={replaceLatestAnswerInHistory}
            mode={mode}
            isLoading={Boolean(initialThreadId) && threadLoading}
            isSubmitting={isSubmitting}
            disableSubmission={disableSubmission}
            pendingQuestion={pendingQuestion}
            displayRunId={displayRunId}
            errorMessage={mutationErrorMessage}
            onModeChange={setMode}
            onSubmit={handleSubmitQuestion}
            onSuggestedFollowup={handleSubmitQuestion}
            isRefreshing={Boolean(initialThreadId) && threadFetching && !threadLoading}
          />
        </div>

        <div className="space-y-4">
          <CollapsibleRail
            title="线程"
            description="继续最近一条线程，别把上下文切断。"
            badge={<Badge variant="outline">{threadItems.length}</Badge>}
            defaultOpen={threadsOpen}
            className="space-y-4"
          >
            <div className="space-y-4 p-4">
              {threadsPanel}
              {recommendedPanel}
            </div>
          </CollapsibleRail>

          <CollapsibleRail
            title="证据与摘要"
            description="当前回答的证据卡和运行摘要。"
            badge={<Badge variant="outline">{activeResponse?.evidence_cards?.length ?? 0}</Badge>}
            defaultOpen={evidenceOpen}
            className="space-y-4"
          >
            <div className="space-y-4 p-4">
              {summaryPanel}
              <EvidenceSidePanel response={activeResponse} displayRunId={displayRunId} />
            </div>
          </CollapsibleRail>
        </div>
      </div>

      <div className="space-y-4 lg:hidden">
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant={threadsOpen ? 'default' : 'outline'} size="sm" onClick={() => setThreadsOpen((value) => !value)}>
            线程
          </Button>
          <Button type="button" variant={evidenceOpen ? 'default' : 'outline'} size="sm" onClick={() => setEvidenceOpen((value) => !value)}>
            证据
          </Button>
        </div>

        {threadsOpen ? (
          <div className="space-y-4">
            {threadsPanel}
            {recommendedPanel}
          </div>
        ) : null}

        {threadErrorMessage ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>线程暂时打不开</AlertTitle>
            <AlertDescription>{threadErrorMessage}</AlertDescription>
          </Alert>
        ) : null}

        <CopilotChatPanel
          projectName={projectName}
          threadTitle={threadDetail?.title || (initialThreadId ? '正在载入线程...' : '证据副驾')}
          messages={threadDetail?.messages || []}
          response={activeResponse}
          replaceLatestAnswerInHistory={replaceLatestAnswerInHistory}
          mode={mode}
          isLoading={Boolean(initialThreadId) && threadLoading}
          isSubmitting={isSubmitting}
          disableSubmission={disableSubmission}
          pendingQuestion={pendingQuestion}
          displayRunId={displayRunId}
          errorMessage={mutationErrorMessage}
          onModeChange={setMode}
          onSubmit={handleSubmitQuestion}
          onSuggestedFollowup={handleSubmitQuestion}
          isRefreshing={Boolean(initialThreadId) && threadFetching && !threadLoading}
        />

        {evidenceOpen ? (
          <div className="space-y-4">
            {summaryPanel}
            <EvidenceSidePanel response={activeResponse} displayRunId={displayRunId} />
          </div>
        ) : null}
      </div>
    </div>
  )
}
