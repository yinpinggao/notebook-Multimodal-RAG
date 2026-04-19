'use client'

import Link from 'next/link'
import { useMemo } from 'react'
import {
  ArrowRight,
  Bot,
  FolderKanban,
  MessageSquare,
  Plus,
  Settings,
  Sparkles,
} from 'lucide-react'

import { EmptyState } from '@/components/common/EmptyState'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { AppShell } from '@/components/layout/AppShell'
import { ProjectCard } from '@/components/projects/project-card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { buildAssistantUrl } from '@/lib/assistant-workspace'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import { useModelDefaults, useModels } from '@/lib/hooks/use-models'
import { useProjectThreads } from '@/lib/hooks/use-project-evidence'
import { useProjects } from '@/lib/hooks/use-projects'
import { useTranslation } from '@/lib/hooks/use-translation'
import { projectSummaryToWorkspaceSummary } from '@/lib/project-workspace'
import { useAssistantWorkspaceStore } from '@/lib/stores/assistant-workspace-store'

function formatDefaultSummary(params: {
  models: Array<{ id: string; name: string }>
  defaults: {
    default_chat_model?: string | null
    default_vision_model?: string | null
    default_embedding_model?: string | null
  } | null | undefined
  labels: {
    chat: string
    vision: string
    embedding: string
  }
}) {
  const resolveName = (modelId?: string | null) =>
    params.models.find((model) => model.id === modelId)?.name || null

  const chat = resolveName(params.defaults?.default_chat_model)
  const vision = resolveName(params.defaults?.default_vision_model)
  const embedding = resolveName(params.defaults?.default_embedding_model)

  return [
    chat ? params.labels.chat.replace('{name}', chat) : null,
    vision ? params.labels.vision.replace('{name}', vision) : null,
    embedding ? params.labels.embedding.replace('{name}', embedding) : null,
  ].filter(Boolean) as string[]
}

export default function DashboardHomePage() {
  const { t } = useTranslation()
  const { openNotebookDialog, openSourceDialog } = useCreateDialogs()
  const { lastProjectId } = useAssistantWorkspaceStore()
  const { data: projectSummaries = [], isLoading: projectsLoading } = useProjects(false)
  const { data: models = [], isLoading: modelsLoading } = useModels()
  const { data: defaults } = useModelDefaults()
  const continueProjectId = useMemo(() => {
    if (lastProjectId && projectSummaries.some((project) => project.id === lastProjectId)) {
      return lastProjectId
    }
    return projectSummaries
      .slice()
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0]?.id || ''
  }, [lastProjectId, projectSummaries])
  const { data: lastProjectThreads = [] } = useProjectThreads(continueProjectId)

  const projects = useMemo(
    () =>
      [...projectSummaries]
        .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
        .map((project) => projectSummaryToWorkspaceSummary(project)),
    [projectSummaries]
  )

  const lastProject = projects.find((project) => project.id === continueProjectId) || projects[0]
  const recentThread = useMemo(
    () =>
      [...lastProjectThreads]
        .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0],
    [lastProjectThreads]
  )
  const defaultSummary = formatDefaultSummary({
    models,
    defaults,
    labels: {
      chat: t.assistant.dashboardModelChat,
      vision: t.assistant.dashboardModelVision,
      embedding: t.assistant.dashboardModelEmbedding,
    },
  })
  const needsModelSetup =
    models.length === 0 ||
    (!defaults?.default_chat_model && !defaults?.default_vision_model && !defaults?.default_embedding_model)

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-6 p-6">
          <header className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">{t.navigation.dashboard}</Badge>
              <Badge variant="secondary">{t.assistant.workspace}</Badge>
            </div>
            <div className="space-y-2">
              <h1 className="text-3xl font-semibold tracking-tight">{t.navigation.dashboard}</h1>
              <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
                {t.assistant.dashboardIntro}
              </p>
            </div>
          </header>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(320px,1fr)]">
            <section className="space-y-6">
              <Card className="border-border/70">
                <CardHeader>
                  <CardTitle>{t.assistant.continueTitle}</CardTitle>
                  <CardDescription>{t.assistant.continueDescription}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {projectsLoading ? (
                    <div className="flex min-h-32 items-center justify-center">
                      <LoadingSpinner size="lg" />
                    </div>
                  ) : lastProject ? (
                    <>
                      <div className="rounded-md border border-border/70 p-4">
                        <div className="text-sm font-medium">{lastProject.name}</div>
                        <div className="mt-2 text-sm leading-6 text-muted-foreground">
                          {lastProject.description || t.assistant.continueProjectFallback}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button asChild>
                          <Link href={buildAssistantUrl({ projectId: lastProject.id, view: 'knowledge' })}>
                            {t.assistant.knowledgeHub}
                            <ArrowRight className="ml-2 h-4 w-4" />
                          </Link>
                        </Button>
                        <Button asChild variant="outline">
                          <Link
                            href={buildAssistantUrl({
                              projectId: lastProject.id,
                              view: 'workspace',
                              threadId: recentThread?.id || null,
                            })}
                          >
                            <MessageSquare className="mr-2 h-4 w-4" />
                            {recentThread ? t.assistant.continueThread : t.assistant.workspace}
                          </Link>
                        </Button>
                      </div>
                    </>
                  ) : (
                    <EmptyState
                      icon={FolderKanban}
                      title={t.assistant.emptyWorkspaceTitle}
                      description={t.assistant.noProjectYetDescription}
                      action={<Button onClick={openNotebookDialog}>{t.assistant.createProject}</Button>}
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="border-border/70">
                <CardHeader className="flex flex-row items-start justify-between gap-4">
                  <div>
                    <CardTitle>{t.navigation.projects}</CardTitle>
                    <CardDescription>{t.assistant.projectsDescription}</CardDescription>
                  </div>
                  <Button onClick={openNotebookDialog}>
                    <Plus className="mr-2 h-4 w-4" />
                    {t.assistant.createProject}
                  </Button>
                </CardHeader>
                <CardContent>
                  {projectsLoading ? (
                    <div className="flex min-h-40 items-center justify-center">
                      <LoadingSpinner size="lg" />
                    </div>
                  ) : projects.length === 0 ? (
                    <EmptyState
                      icon={FolderKanban}
                      title={t.assistant.noProjectsTitle}
                      description={t.assistant.noProjectsDescription}
                    />
                  ) : (
                    <div className="grid gap-4 md:grid-cols-2">
                      {projects.slice(0, 6).map((project) => (
                        <ProjectCard
                          key={project.id}
                          project={project}
                          href={buildAssistantUrl({ projectId: project.id, view: 'knowledge' })}
                          ctaLabel={t.assistant.knowledgeHub}
                        />
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </section>

            <aside className="space-y-6">
              <Card className="border-border/70">
                <CardHeader>
                  <CardTitle>{t.common.quickActions}</CardTitle>
                  <CardDescription>{t.assistant.quickActionsDescription}</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-2">
                  <Button className="justify-start" onClick={openNotebookDialog}>
                    <Plus className="mr-2 h-4 w-4" />
                    {t.assistant.createProject}
                  </Button>
                  <Button className="justify-start" variant="outline" onClick={openSourceDialog}>
                    <FolderKanban className="mr-2 h-4 w-4" />
                    {t.common.newSource}
                  </Button>
                  <Button asChild className="justify-start" variant="outline">
                    <Link href="/models">
                      <Bot className="mr-2 h-4 w-4" />
                      {t.navigation.models}
                    </Link>
                  </Button>
                  <Button asChild className="justify-start" variant="outline">
                    <Link href="/settings">
                      <Settings className="mr-2 h-4 w-4" />
                      {t.navigation.settings}
                    </Link>
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-border/70">
                <CardHeader>
                  <CardTitle>{t.assistant.setupStatusTitle}</CardTitle>
                  <CardDescription>{t.assistant.setupStatusDescription}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {modelsLoading ? (
                    <div className="flex min-h-24 items-center justify-center">
                      <LoadingSpinner />
                    </div>
                  ) : needsModelSetup ? (
                    <div className="rounded-md border border-dashed border-border/70 p-4">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Sparkles className="h-4 w-4 text-primary" />
                        {t.assistant.configureModels}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        {t.assistant.configureModelsDescription}
                      </p>
                      <Button asChild className="mt-4">
                        <Link href="/models">{t.navigation.models}</Link>
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="rounded-md border border-border/70 p-4">
                        <div className="text-sm font-medium">{t.assistant.availableModels}</div>
                        <div className="mt-2 text-2xl font-semibold">{models.length}</div>
                        <div className="mt-2 text-sm text-muted-foreground">
                          {defaultSummary.join(' • ')}
                        </div>
                      </div>
                      <Button asChild variant="outline" className="w-full">
                        <Link href="/models">{t.navigation.models}</Link>
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </aside>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
