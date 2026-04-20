'use client'

import { useMemo } from 'react'

import { useProjectArtifacts } from '@/lib/hooks/use-project-artifacts'
import { useProjectCompares } from '@/lib/hooks/use-project-compare'
import { useProjectThread, useProjectThreads } from '@/lib/hooks/use-project-evidence'
import { useProjectMemory } from '@/lib/hooks/use-project-memory'
import { useProjectOverview } from '@/lib/hooks/use-projects'
import { useProjectRuns } from '@/lib/hooks/use-project-runs'
import { useSources } from '@/lib/hooks/use-sources'
import { buildZycProjectRecord } from '@/lib/zhiyancang/adapters'

interface UseZycProjectDetailOptions {
  threadId?: string
}

export function useZycProjectDetail(
  projectId: string,
  options?: UseZycProjectDetailOptions
) {
  const overviewQuery = useProjectOverview(projectId)
  const threadsQuery = useProjectThreads(projectId)
  const resolvedThreadId = options?.threadId || threadsQuery.data?.[0]?.id
  const threadQuery = useProjectThread(projectId, resolvedThreadId)
  const sourcesQuery = useSources(projectId)
  const comparesQuery = useProjectCompares(projectId)
  const memoryQuery = useProjectMemory(projectId)
  const artifactsQuery = useProjectArtifacts(projectId)
  const runsQuery = useProjectRuns(projectId)

  const data = useMemo(() => {
    if (!overviewQuery.data) {
      return undefined
    }

    return buildZycProjectRecord({
      overview: overviewQuery.data,
      threads: threadsQuery.data || [],
      thread: threadQuery.data || null,
      sources: sourcesQuery.data || [],
      compares: comparesQuery.data || [],
      memories: memoryQuery.data || [],
      artifacts: artifactsQuery.data || [],
      runs: runsQuery.data || [],
    })
  }, [
    artifactsQuery.data,
    comparesQuery.data,
    memoryQuery.data,
    overviewQuery.data,
    runsQuery.data,
    sourcesQuery.data,
    threadQuery.data,
    threadsQuery.data,
  ])

  const isLoading =
    overviewQuery.isLoading ||
    threadsQuery.isLoading ||
    sourcesQuery.isLoading ||
    comparesQuery.isLoading ||
    memoryQuery.isLoading ||
    artifactsQuery.isLoading ||
    runsQuery.isLoading ||
    (!!resolvedThreadId && threadQuery.isLoading)

  const error =
    overviewQuery.error ||
    threadsQuery.error ||
    threadQuery.error ||
    sourcesQuery.error ||
    comparesQuery.error ||
    memoryQuery.error ||
    artifactsQuery.error ||
    runsQuery.error ||
    null

  const refetch = async () => {
    await Promise.all([
      overviewQuery.refetch(),
      threadsQuery.refetch(),
      resolvedThreadId ? threadQuery.refetch() : Promise.resolve(),
      sourcesQuery.refetch(),
      comparesQuery.refetch(),
      memoryQuery.refetch(),
      artifactsQuery.refetch(),
      runsQuery.refetch(),
    ])
  }

  return {
    data,
    error,
    isLoading,
    isError: Boolean(error),
    refetch,
    meta: {
      overview: overviewQuery.data,
      threads: threadsQuery.data || [],
      activeThread: threadQuery.data || null,
      activeThreadId: resolvedThreadId || null,
      sources: sourcesQuery.data || [],
      compares: comparesQuery.data || [],
      memories: memoryQuery.data || [],
      artifacts: artifactsQuery.data || [],
      runs: runsQuery.data || [],
    },
  }
}
