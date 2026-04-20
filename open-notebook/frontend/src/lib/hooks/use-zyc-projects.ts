'use client'

import { useMemo } from 'react'

import { useProjects } from '@/lib/hooks/use-projects'
import { mapProjectSummaryToZycProjectCard } from '@/lib/zhiyancang/adapters'

export function useZycProjects() {
  const query = useProjects(false)

  const data = useMemo(() => {
    if (!query.data) {
      return undefined
    }

    const projects = query.data.map(mapProjectSummaryToZycProjectCard)

    return {
      projects,
      latestProjectId: query.data[0]?.id || null,
    }
  }, [query.data])

  return {
    ...query,
    data,
  }
}
