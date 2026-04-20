'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { CodeSnippetBlock } from '@/components/zhiyancang/runs/code-snippet-block'
import { RunCollapsiblePanel } from '@/components/zhiyancang/runs/run-collapsible-panel'
import { RunLogHeader } from '@/components/zhiyancang/runs/run-log-header'
import { ScreenshotStrip } from '@/components/zhiyancang/runs/screenshot-strip'
import { useZycProjectDetail } from '@/lib/hooks/use-zyc-project-detail'
import { formatApiError } from '@/lib/utils/error-handler'

export default function ProjectRunsPage() {
  const params = useParams()
  const projectId = String(params?.projectId || '')
  const { data, error, isLoading } = useZycProjectDetail(projectId)
  const [activeRunId, setActiveRunId] = useState<string | null>(null)

  useEffect(() => {
    if (!data?.runs.length) {
      setActiveRunId(null)
      return
    }

    if (!activeRunId || !data.runs.some((run) => run.id === activeRunId)) {
      setActiveRunId(data.runs[0].id)
    }
  }, [activeRunId, data?.runs])

  const activeRun = data?.runs.find((run) => run.id === activeRunId) || data?.runs[0]

  const sections = useMemo(() => {
    if (!activeRun) {
      return []
    }

    return [
      {
        id: 'goal',
        title: 'Goal / Agents / Evidence',
        content: (
          <div className="space-y-4">
            <div className="rounded-[20px] border border-white/8 bg-white/4 px-4 py-4 text-sm text-white/68">
              <div className="font-medium text-white">Goal</div>
              <div className="mt-2 leading-7">{activeRun.goal}</div>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-[20px] border border-white/8 bg-white/4 px-4 py-4">
                <div className="text-sm font-medium text-white">Evidence Referenced</div>
                <div className="mt-3 space-y-2">
                  {activeRun.evidenceReferenced.length > 0 ? (
                    activeRun.evidenceReferenced.map((item) => (
                      <div
                        key={item}
                        className="rounded-2xl border border-white/8 bg-black/18 px-4 py-3 text-sm text-white/66"
                      >
                        {item}
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-dashed border-white/12 px-4 py-3 text-sm text-white/48">
                      No evidence reads recorded for this run.
                    </div>
                  )}
                </div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-white/4 px-4 py-4">
                <div className="text-sm font-medium text-white">Tools Invoked</div>
                <div className="mt-3 space-y-2">
                  {activeRun.toolsInvoked.length > 0 ? (
                    activeRun.toolsInvoked.map((item) => (
                      <div
                        key={item}
                        className="rounded-2xl border border-white/8 bg-black/18 px-4 py-3 text-sm text-white/66"
                      >
                        {item}
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-dashed border-white/12 px-4 py-3 text-sm text-white/48">
                      No tool calls recorded for this run.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        ),
      },
      {
        id: 'steps',
        title: 'Step-by-step State',
        content: (
          <div className="space-y-4">
            {activeRun.stateTimeline.map((step) => (
              <div key={step.id} className="rounded-[20px] border border-white/8 bg-white/4 px-4 py-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-base font-medium text-white">{step.title}</div>
                  <span className="rounded-full border border-white/10 px-3 py-1 text-xs capitalize text-white/50">
                    {step.status}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-7 text-white/68">{step.detail}</p>
                {step.code ? (
                  <div className="mt-4">
                    <CodeSnippetBlock title={step.title} code={step.code} />
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ),
      },
      {
        id: 'output',
        title: 'Final Output / Exceptions',
        content: (
          <div className="space-y-4">
            <div className="rounded-[20px] border border-white/8 bg-white/4 px-4 py-4 text-sm leading-7 text-white/68">
              {activeRun.finalOutput}
            </div>
            <div className="space-y-2">
              {activeRun.exceptions.length > 0 ? (
                activeRun.exceptions.map((item) => (
                  <div
                    key={item}
                    className="rounded-[20px] border border-[rgba(240,174,67,0.25)] bg-[rgba(240,174,67,0.12)] px-4 py-4 text-sm leading-7 text-white/70"
                  >
                    {item}
                  </div>
                ))
              ) : (
                <div className="rounded-[20px] border border-white/8 bg-white/4 px-4 py-4 text-sm text-white/50">
                  No exception recorded.
                </div>
              )}
            </div>
          </div>
        ),
      },
    ]
  }, [activeRun])

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Runs unavailable</AlertTitle>
        <AlertDescription>{formatApiError(error)}</AlertDescription>
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

  if (!activeRun) {
    return (
      <div className="rounded-[24px] border border-dashed border-white/12 px-6 py-10 text-sm leading-7 text-white/55">
        No run recorded yet. Start from Evidence, Compare, Memory rebuild, or Outputs generation to
        create the first trace.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {data.runs.map((run) => (
          <button
            key={run.id}
            type="button"
            onClick={() => setActiveRunId(run.id)}
            className={`rounded-full border px-3 py-2 text-sm transition ${
              run.id === activeRun.id
                ? 'border-white/16 bg-white/12 text-white'
                : 'border-white/8 bg-white/4 text-white/60 hover:border-white/14 hover:bg-white/8 hover:text-white'
            }`}
          >
            {run.goal}
          </button>
        ))}
      </div>

      <RunLogHeader run={activeRun} />
      <RunCollapsiblePanel sections={sections} />
      {activeRun.screenshots.length > 0 ? (
        <ScreenshotStrip items={activeRun.screenshots} />
      ) : (
        <div className="rounded-[24px] border border-dashed border-white/12 px-6 py-8 text-sm text-white/50">
          No screenshots were captured for this run.
        </div>
      )}
    </div>
  )
}
