'use client'

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { sourcesApi } from '@/lib/api/sources'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useCredentialStatus } from '@/lib/hooks/use-credentials'
import { useProjectEvalJobs } from '@/lib/hooks/use-admin-evals'
import { useCommandJobs } from '@/lib/hooks/use-admin-jobs'
import { useModelDefaults, useModels } from '@/lib/hooks/use-models'
import { useSettings } from '@/lib/hooks/use-settings'
import { mapLibraryModel, mapSystemModel } from '@/lib/zhiyancang/adapters'

export function useZycLibrary() {
  const sourcesQuery = useQuery({
    queryKey: QUERY_KEYS.sources(),
    queryFn: () =>
      sourcesApi.list({
        sort_by: 'updated',
        sort_order: 'desc',
      }),
  })

  const data = useMemo(
    () => (sourcesQuery.data ? mapLibraryModel(sourcesQuery.data) : undefined),
    [sourcesQuery.data]
  )

  return {
    ...sourcesQuery,
    data,
  }
}

export function useZycSystem() {
  const modelsQuery = useModels()
  const defaultsQuery = useModelDefaults()
  const settingsQuery = useSettings()
  const jobsQuery = useCommandJobs({ limit: 12 })
  const evalJobsQuery = useProjectEvalJobs(12)
  const credentialsQuery = useCredentialStatus()

  const data = useMemo(() => {
    if (!modelsQuery.data) {
      return undefined
    }

    return mapSystemModel({
      models: modelsQuery.data,
      defaults: defaultsQuery.data,
      settings: settingsQuery.data,
      jobs: jobsQuery.data || [],
      evalJobs: evalJobsQuery.data || [],
      credentials: credentialsQuery.data,
    })
  }, [
    credentialsQuery.data,
    defaultsQuery.data,
    evalJobsQuery.data,
    jobsQuery.data,
    modelsQuery.data,
    settingsQuery.data,
  ])

  const error =
    modelsQuery.error ||
    defaultsQuery.error ||
    settingsQuery.error ||
    jobsQuery.error ||
    evalJobsQuery.error ||
    credentialsQuery.error ||
    null

  return {
    data,
    error,
    isLoading:
      modelsQuery.isLoading ||
      defaultsQuery.isLoading ||
      settingsQuery.isLoading ||
      jobsQuery.isLoading ||
      evalJobsQuery.isLoading ||
      credentialsQuery.isLoading,
    isError: Boolean(error),
  }
}
