'use client'

import { useParams } from 'next/navigation'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { NextStepsList } from '@/components/zhiyancang/overview/next-steps-list'
import { OverviewStickyRail } from '@/components/zhiyancang/overview/overview-sticky-rail'
import { OverviewSummaryCard } from '@/components/zhiyancang/overview/overview-summary-card'
import { PhaseProgress } from '@/components/zhiyancang/overview/phase-progress'
import { RiskAlertList } from '@/components/zhiyancang/overview/risk-alert-list'
import { useZycProjectDetail } from '@/lib/hooks/use-zyc-project-detail'
import { formatApiError } from '@/lib/utils/error-handler'

export default function ProjectOverviewPage() {
  const params = useParams()
  const projectId = String(params?.projectId || '')
  const { data, error, isLoading } = useZycProjectDetail(projectId)

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Overview unavailable</AlertTitle>
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

  return (
    <div className="space-y-6">
      <PhaseProgress currentPhase={data.project.phase} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.18fr)_minmax(320px,0.82fr)]">
        <div className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <OverviewSummaryCard title="Project Goal" content={data.overview.goal} icon="goal" />
            <OverviewSummaryCard
              title="Key Questions"
              content={data.overview.keyQuestions.join(' • ')}
              icon="questions"
            />
          </div>
          <OverviewSummaryCard
            title="Current Conclusion"
            content={data.overview.currentConclusion}
            icon="conclusion"
          />
          <RiskAlertList items={data.overview.riskAlerts} />
          <NextStepsList steps={data.overview.nextSteps} />
        </div>

        <OverviewStickyRail overview={data.overview} />
      </div>
    </div>
  )
}
