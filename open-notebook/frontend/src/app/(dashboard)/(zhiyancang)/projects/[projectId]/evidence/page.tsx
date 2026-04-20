'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import {
  faArrowUpRightFromSquare,
  faComments,
  faPlus,
  faSpinner,
  faWandMagicSparkles,
} from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EvidenceFilterPanel } from '@/components/zhiyancang/evidence/evidence-filter-panel'
import { EvidenceMasonry } from '@/components/zhiyancang/evidence/evidence-masonry'
import { EvidenceTypeTabs } from '@/components/zhiyancang/evidence/evidence-type-tabs'
import { useAskProject, useFollowupProjectThread } from '@/lib/hooks/use-project-evidence'
import { useZycProjectDetail } from '@/lib/hooks/use-zyc-project-detail'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import {
  PROJECT_ASK_MODE_OPTIONS,
  buildProjectEvidencePath,
  evidenceThreadIdFromRoute,
} from '@/lib/project-evidence'
import { formatProjectTimestamp } from '@/lib/project-workspace'
import { formatApiError } from '@/lib/utils/error-handler'

function buildAgentHint(params: {
  retrievalMode: string
  searchMode: string
  threadId?: string | null
}) {
  return `zyc:${params.retrievalMode}:${params.searchMode}:${params.threadId ? 'followup' : 'ask'}`
}

export default function ProjectEvidencePage() {
  const params = useParams()
  const router = useRouter()
  const projectId = String(params?.projectId || '')
  const routeThreadId =
    typeof params?.threadId === 'string' ? evidenceThreadIdFromRoute(params.threadId) : undefined
  const { data, error, isLoading, meta } = useZycProjectDetail(projectId, {
    threadId: routeThreadId,
  })
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<'auto' | 'text' | 'visual' | 'mixed'>('auto')
  const { activeSearchMode, workspaceRetrievalMode } = useZycUIStore()

  const askProject = useAskProject(projectId)
  const followupProject = useFollowupProjectThread(projectId, meta.activeThreadId || undefined)
  const isSubmitting = askProject.isPending || followupProject.isPending

  const activeThread = meta.activeThread
  const threads = meta.threads
  const recommendedQuestions = useMemo(() => {
    const items = data?.overview.keyQuestions || meta.overview?.recommended_questions || []
    return items.slice(0, 4)
  }, [data?.overview.keyQuestions, meta.overview?.recommended_questions])

  const errorMessage = error ? formatApiError(error) : null

  const handleSubmit = async (nextQuestion: string) => {
    if (!nextQuestion.trim()) {
      return
    }

    const payload = {
      question: nextQuestion.trim(),
      mode,
      memory_ids: meta.memories
        .filter((memory) => memory.scope === 'project')
        .slice(0, 12)
        .map((memory) => memory.id),
      agent: buildAgentHint({
        retrievalMode: workspaceRetrievalMode,
        searchMode: activeSearchMode,
        threadId: meta.activeThreadId,
      }),
    }

    try {
      const response = meta.activeThreadId
        ? await followupProject.mutateAsync(payload)
        : await askProject.mutateAsync(payload)

      setQuestion('')

      if (response.thread_id) {
        router.push(buildProjectEvidencePath(projectId, response.thread_id))
      }
    } catch {
      // Inline error state handles this.
    }
  }

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Evidence unavailable</AlertTitle>
        <AlertDescription>{errorMessage}</AlertDescription>
      </Alert>
    )
  }

  if (isLoading || !data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <section className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="space-y-4">
          <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-medium text-white">Threads</div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
                onClick={() => router.push(buildProjectEvidencePath(projectId))}
              >
                <FontAwesomeIcon icon={faPlus} className="mr-2 text-xs" />
                New
              </Button>
            </div>
            <div className="mt-4 space-y-3">
              {threads.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-white/12 px-4 py-5 text-sm leading-7 text-white/52">
                  No thread yet. Start from a recommended question or write your own.
                </div>
              ) : (
                threads.map((thread) => {
                  const isActive = thread.id === meta.activeThreadId

                  return (
                    <button
                      key={thread.id}
                      type="button"
                      onClick={() => router.push(buildProjectEvidencePath(projectId, thread.id))}
                      className={`w-full rounded-[20px] border px-4 py-4 text-left transition ${
                        isActive
                          ? 'border-white/16 bg-white/12 text-white'
                          : 'border-white/8 bg-white/4 text-white/68 hover:border-white/14 hover:bg-white/8'
                      }`}
                    >
                      <div className="text-sm font-medium">{thread.title}</div>
                      <div className="mt-2 text-xs text-white/42">
                        {formatProjectTimestamp(thread.updated_at)} · {thread.message_count} messages
                      </div>
                      {thread.last_question ? (
                        <div className="mt-3 line-clamp-2 text-xs leading-5 text-white/52">
                          {thread.last_question}
                        </div>
                      ) : null}
                    </button>
                  )
                })
              )}
            </div>
          </div>

          <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
            <div className="flex items-center gap-3 text-sm font-medium text-white">
              <FontAwesomeIcon icon={faWandMagicSparkles} className="text-white/52" />
              Recommended Questions
            </div>
            <div className="mt-4 space-y-3">
              {recommendedQuestions.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-white/12 px-4 py-5 text-sm text-white/52">
                  No suggestions yet. Rebuild the overview after importing more sources.
                </div>
              ) : (
                recommendedQuestions.map((item) => (
                  <button
                    key={item}
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => {
                      void handleSubmit(item)
                    }}
                    className="w-full rounded-[20px] border border-white/8 bg-white/4 px-4 py-4 text-left text-sm leading-7 text-white/68 transition hover:border-white/14 hover:bg-white/8 disabled:opacity-60"
                  >
                    {item}
                  </button>
                ))
              )}
            </div>
          </div>

          <EvidenceFilterPanel evidence={data.evidence} />
        </aside>

        <div className="space-y-4">
          <div className="zyc-glass rounded-[24px] px-5 py-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-sm font-medium text-white">
                  {meta.activeThreadId ? 'Continue Thread' : 'Start Evidence Ask'}
                </div>
                <p className="mt-1 text-sm leading-6 text-white/58">
                  Ask first in Evidence. The current thread drives workspace, outputs, and run
                  trace.
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                {PROJECT_ASK_MODE_OPTIONS.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setMode(item.value)}
                    className={`rounded-full border px-3 py-2 text-xs transition ${
                      mode === item.value
                        ? 'border-white/16 bg-white/14 text-white'
                        : 'border-white/8 bg-white/4 text-white/56 hover:border-white/14 hover:bg-white/8 hover:text-white'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-4">
              <Textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder={
                  meta.activeThreadId
                    ? 'Ask a grounded follow-up...'
                    : 'Ask the first evidence-grounded question for this project...'
                }
                className="min-h-28 rounded-[20px] border-white/10 bg-white/6 text-white placeholder:text-white/30"
              />
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs text-white/40">
                Retrieval {workspaceRetrievalMode.toUpperCase()} · Filter {activeSearchMode.toUpperCase()}
              </div>
              <Button
                type="button"
                onClick={() => {
                  void handleSubmit(question)
                }}
                disabled={isSubmitting || !question.trim()}
                className="rounded-full bg-white text-zinc-950 hover:bg-white/92"
              >
                {isSubmitting ? (
                  <FontAwesomeIcon icon={faSpinner} className="mr-2 animate-spin" />
                ) : (
                  <FontAwesomeIcon icon={faComments} className="mr-2" />
                )}
                {meta.activeThreadId ? 'Send Follow-up' : 'Ask with Evidence'}
              </Button>
            </div>

            {askProject.error || followupProject.error ? (
              <Alert variant="destructive" className="mt-4">
                <AlertTitle>Ask failed</AlertTitle>
                <AlertDescription>
                  {formatApiError(followupProject.error || askProject.error)}
                </AlertDescription>
              </Alert>
            ) : null}
          </div>

          <div className="rounded-[24px] border border-white/8 bg-white/4 px-5 py-5">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-medium text-white">
                {activeThread?.title || 'No active thread'}
              </div>
              {meta.activeThreadId ? (
                <Button
                  asChild
                  variant="outline"
                  className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
                >
                  <Link href={`/projects/${encodeURIComponent(projectId)}/workspace`}>
                    <FontAwesomeIcon icon={faArrowUpRightFromSquare} className="mr-2" />
                    Open Workspace
                  </Link>
                </Button>
              ) : null}
            </div>

            <div className="mt-4 text-sm leading-7 text-white/68">
              {activeThread?.latest_response?.answer ||
                'The current project does not have an evidence answer yet. Start with a first question or pick a recommended prompt.'}
            </div>

            {activeThread?.latest_response?.suggested_followups?.length ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {activeThread.latest_response.suggested_followups.slice(0, 4).map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setQuestion(item)}
                    className="rounded-full border border-white/8 bg-white/4 px-3 py-2 text-xs text-white/56 transition hover:border-white/14 hover:bg-white/8 hover:text-white"
                  >
                    {item}
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <EvidenceTypeTabs />

          {data.evidence.items.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-white/12 px-6 py-12 text-sm leading-7 text-white/55">
              No evidence cards yet. Ask a project question first, or open an existing thread.
            </div>
          ) : (
            <EvidenceMasonry evidence={data.evidence} />
          )}
        </div>
      </section>
    </div>
  )
}
