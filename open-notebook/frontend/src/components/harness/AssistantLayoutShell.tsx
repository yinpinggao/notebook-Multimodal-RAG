'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { AssistantTopBar } from '@/components/harness/AssistantTopBar'
import {
  mergeAssistantSearchParams,
  resolveAssistantProjectId,
  sanitizeAssistantView,
  sanitizeHarnessAgent,
} from '@/lib/assistant-workspace'
import { useProjects } from '@/lib/hooks/use-projects'
import { useAssistantWorkspaceStore } from '@/lib/stores/assistant-workspace-store'

interface AssistantLayoutShellProps {
  children: React.ReactNode
}

export function AssistantLayoutShell({ children }: AssistantLayoutShellProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const {
    currentProjectId,
    lastProjectId,
    setCurrentAgent,
    setCurrentProject,
    setCurrentThread,
    setCurrentView,
    setLastProjectId,
  } = useAssistantWorkspaceStore()
  const {
    data: projects = [],
    isLoading,
  } = useProjects(false)

  const requestedProjectId = searchParams.get('project')
  const requestedThreadId = searchParams.get('thread') || undefined
  const requestedView = sanitizeAssistantView(searchParams.get('view'))
  const requestedAgent = sanitizeHarnessAgent(searchParams.get('agent'))

  const resolvedProjectId = resolveAssistantProjectId({
    projects,
    requestedProjectId,
    lastProjectId,
  })

  useEffect(() => {
    setCurrentView(requestedView)
    setCurrentAgent(requestedAgent)
    setCurrentThread(requestedThreadId)
  }, [
    requestedAgent,
    requestedThreadId,
    requestedView,
    setCurrentAgent,
    setCurrentThread,
    setCurrentView,
  ])

  useEffect(() => {
    setCurrentProject(resolvedProjectId)
    if (resolvedProjectId) {
      setLastProjectId(resolvedProjectId)
    }
  }, [resolvedProjectId, setCurrentProject, setLastProjectId])

  useEffect(() => {
    if (isLoading) {
      return
    }

    if (!resolvedProjectId) {
      return
    }

    if (requestedProjectId === resolvedProjectId && currentProjectId === resolvedProjectId) {
      return
    }

    router.replace(
      mergeAssistantSearchParams(searchParams, {
        projectId: resolvedProjectId,
        threadId: requestedProjectId === resolvedProjectId ? requestedThreadId : null,
      }),
      { scroll: false }
    )
  }, [
    currentProjectId,
    isLoading,
    requestedProjectId,
    requestedThreadId,
    resolvedProjectId,
    router,
    searchParams,
  ])

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <AssistantTopBar projects={projects} isLoading={isLoading} />
      {children}
    </div>
  )
}
