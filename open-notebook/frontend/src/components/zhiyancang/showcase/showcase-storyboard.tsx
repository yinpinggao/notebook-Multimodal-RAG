'use client'

import { EvidenceMasonry } from '@/components/zhiyancang/evidence/evidence-masonry'
import { CompareResultGrid } from '@/components/zhiyancang/compare/compare-result-grid'
import { MemorySectionBoard } from '@/components/zhiyancang/memory/memory-section-board'
import { OutputsWaterfall } from '@/components/zhiyancang/outputs/outputs-waterfall'
import { RunCollapsiblePanel } from '@/components/zhiyancang/runs/run-collapsible-panel'
import { RunLogHeader } from '@/components/zhiyancang/runs/run-log-header'
import { ScreenshotStrip } from '@/components/zhiyancang/runs/screenshot-strip'
import { NextStepsList } from '@/components/zhiyancang/overview/next-steps-list'
import { OverviewSummaryCard } from '@/components/zhiyancang/overview/overview-summary-card'
import { RiskAlertList } from '@/components/zhiyancang/overview/risk-alert-list'
import { ShowcaseSectionFrame } from '@/components/zhiyancang/showcase/showcase-section-frame'
import type { ZycProjectRecord } from '@/lib/zhiyancang/types'

export function ShowcaseStoryboard({ record }: { record: ZycProjectRecord }) {
  const activeRun = record.runs[0]

  return (
    <div className="space-y-6">
      <ShowcaseSectionFrame
        title="Overview"
        description="Understand the project, the open risks, and the next moves in one screen."
      >
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <div className="space-y-4">
            <OverviewSummaryCard title="Project Goal" content={record.overview.goal} icon="goal" />
            <OverviewSummaryCard title="Current Conclusion" content={record.overview.currentConclusion} icon="conclusion" />
          </div>
          <div className="space-y-4">
            <RiskAlertList items={record.overview.riskAlerts} />
            <NextStepsList steps={record.overview.nextSteps} />
          </div>
        </div>
      </ShowcaseSectionFrame>

      <ShowcaseSectionFrame
        title="Evidence"
        description="Browse cards across documents, web, images, audio, and visual evidence."
      >
        <EvidenceMasonry evidence={record.evidence} showAll />
      </ShowcaseSectionFrame>

      <ShowcaseSectionFrame
        title="Compare"
        description="Surface similarities, differences, conflicts, and missing items at a glance."
      >
        <CompareResultGrid compare={record.compare} />
      </ShowcaseSectionFrame>

      <ShowcaseSectionFrame
        title="Memory"
        description="Review project memory as pending, stable, frozen, or decayed."
      >
        <MemorySectionBoard items={record.memory} />
      </ShowcaseSectionFrame>

      <ShowcaseSectionFrame
        title="Outputs"
        description="Keep regenerated drafts and high-signal summaries in the same surface."
      >
        <OutputsWaterfall items={record.outputs} />
      </ShowcaseSectionFrame>

      <ShowcaseSectionFrame
        title="Runs"
        description="Replay the run goal, steps, tools, exceptions, and screenshots."
      >
        {activeRun ? (
          <div className="space-y-4">
            <RunLogHeader run={activeRun} />
            <RunCollapsiblePanel
              sections={[
                {
                  id: 'story-run-state',
                  title: 'Step-by-step State',
                  content: (
                    <div className="space-y-3">
                      {activeRun.stateTimeline.map((step) => (
                        <div key={step.id} className="rounded-2xl border border-white/8 bg-white/4 px-4 py-3 text-sm text-white/68">
                          {step.title} · {step.detail}
                        </div>
                      ))}
                    </div>
                  ),
                },
              ]}
            />
            <ScreenshotStrip items={activeRun.screenshots} />
          </div>
        ) : (
          <div className="rounded-[24px] border border-dashed border-white/12 px-6 py-8 text-sm text-white/55">
            No run is available for the showcase yet.
          </div>
        )}
      </ShowcaseSectionFrame>
    </div>
  )
}
