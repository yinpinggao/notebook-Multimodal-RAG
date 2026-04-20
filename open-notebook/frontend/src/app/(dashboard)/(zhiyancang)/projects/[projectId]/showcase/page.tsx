'use client'

import { useEffect } from 'react'
import { useParams } from 'next/navigation'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { ShowcaseStoryboard } from '@/components/zhiyancang/showcase/showcase-storyboard'
import { useZycProjectDetail } from '@/lib/hooks/use-zyc-project-detail'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import { formatApiError } from '@/lib/utils/error-handler'

export default function ProjectShowcasePage() {
  const params = useParams()
  const projectId = String(params?.projectId || '')
  const { data, error, isLoading } = useZycProjectDetail(projectId)
  const { setDemoMode } = useZycUIStore()

  useEffect(() => {
    setDemoMode(true)
    return () => setDemoMode(false)
  }, [setDemoMode])

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Showcase unavailable</AlertTitle>
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

  return <ShowcaseStoryboard record={data} />
}
