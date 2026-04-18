import {
  NotebookResponse,
  ProjectOverviewResponse,
  ProjectSummaryResponse,
  ProjectTimelineEventResponse,
  SourceListResponse,
} from '@/lib/types/api'
import { notebookIdToProjectId, projectIdToNotebookId } from '@/lib/project-alias'

export interface ProjectWorkspaceSummary {
  id: string
  notebookId: string
  name: string
  description: string
  status: 'active' | 'archived'
  createdAt: string
  updatedAt: string
  sourceCount: number
  noteCount: number | null
  artifactCount: number
  memoryCount: number
}

export interface ProjectTimelineEvent {
  id: string
  title: string
  description: string
  occurredAt?: string | null
  sourceRefs: string[]
}

export interface ProjectOverviewStats {
  noteCount: number | null
  embeddedSourceCount: number
  visualReadyCount: number
  insightCount: number
}

export interface ProjectOverviewViewModel {
  project: ProjectWorkspaceSummary
  sourceCount: number
  artifactCount: number
  memoryCount: number
  topics: string[]
  keywords: string[]
  risks: string[]
  timelineEvents: ProjectTimelineEvent[]
  recommendedQuestions: string[]
  recentArtifacts: Array<{
    id: string
    title: string
    artifactType: string
    createdAt: string
  }>
  recentRuns: Array<{
    id: string
    runType: string
    status: string
    createdAt: string
  }>
  stats: ProjectOverviewStats
}

const DEFAULT_TOPICS = ['研究目标', '资料结构', '证据线索']

function dedupeStrings(values: Array<string | null | undefined>): string[] {
  const deduped: string[] = []

  values.forEach((value) => {
    const normalized = value?.trim()
    if (normalized && !deduped.includes(normalized)) {
      deduped.push(normalized)
    }
  })

  return deduped
}

function buildRiskList(params: {
  sourceCount: number
  embeddedSourceCount: number
  visualReadyCount: number
  processingSourceCount: number
}): string[] {
  const risks: string[] = []

  if (params.sourceCount === 0) {
    risks.push('尚未导入资料，项目画像和证据回答还没有可依赖的基础材料。')
  }

  if (params.processingSourceCount > 0) {
    risks.push(
      `${params.processingSourceCount} 份资料仍在处理中，当前结论可能还不完整。`
    )
  }

  if (params.sourceCount > 0 && params.embeddedSourceCount === 0) {
    risks.push('文本检索索引还没有准备好，主题归纳和问答召回会受到影响。')
  }

  if (params.sourceCount > 0 && params.visualReadyCount === 0) {
    risks.push('视觉资料还没有建立索引，图表、版面和截图相关问题暂时不够稳。')
  }

  if (risks.length === 0) {
    risks.push('当前资料状态比较稳定，可以先从证据问答或项目综述开始。')
  }

  return risks
}

function buildTimelineEvents(params: {
  projectId: string
  createdAt: string
  updatedAt: string
  sources: SourceListResponse[]
  processingSourceCount: number
}): ProjectTimelineEvent[] {
  const latestSource = [...params.sources].sort((left, right) =>
    right.updated.localeCompare(left.updated)
  )[0]

  const timeline: ProjectTimelineEvent[] = [
    {
      id: `timeline:${params.projectId}:created`,
      title: '创建项目空间',
      description: '项目工作台已经建立，可以开始整理资料和沉淀证据。',
      occurredAt: params.createdAt,
      sourceRefs: [],
    },
  ]

  if (latestSource) {
    timeline.unshift({
      id: `timeline:${params.projectId}:source:${latestSource.id}`,
      title: '最近整理资料',
      description: `${latestSource.title || '未命名资料'} 最近被更新，可继续补充主题和证据。`,
      occurredAt: latestSource.updated,
      sourceRefs: [latestSource.id],
    })
  }

  if (params.processingSourceCount > 0) {
    timeline.unshift({
      id: `timeline:${params.projectId}:processing`,
      title: '资料处理中',
      description: `${params.processingSourceCount} 份资料仍在建立索引，稍后适合重新生成项目画像。`,
      occurredAt: params.updatedAt,
      sourceRefs: [],
    })
  }

  return timeline.slice(0, 4)
}

function buildRecommendedQuestions(topics: string[], hasSources: boolean): string[] {
  if (!hasSources) {
    return [
      '这个项目最值得先导入哪几类资料？',
      '项目总览应该先回答哪些关键问题？',
      '第一轮证据问答适合从什么任务开始？',
    ]
  }

  const firstTopic = topics[0] || '核心主题'
  const secondTopic = topics[1] || '项目目标'

  return [
    `围绕“${firstTopic}”目前最扎实的证据是什么？`,
    `从“${secondTopic}”出发，还缺哪些资料才能形成完整判断？`,
    '如果现在生成项目综述，最需要人工复核的部分会在哪里？',
  ]
}

export function formatProjectTimestamp(value?: string | null): string {
  if (!value) {
    return '待更新'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function toProjectWorkspaceSummary(
  notebook: NotebookResponse
): ProjectWorkspaceSummary {
  return {
    id: notebookIdToProjectId(notebook.id),
    notebookId: notebook.id,
    name: notebook.name,
    description: notebook.description,
    status: notebook.archived ? 'archived' : 'active',
    createdAt: notebook.created,
    updatedAt: notebook.updated,
    sourceCount: notebook.source_count,
    noteCount: notebook.note_count,
    artifactCount: 0,
    memoryCount: 0,
  }
}

export function projectSummaryToWorkspaceSummary(
  project: ProjectSummaryResponse,
  options?: {
    noteCount?: number
  }
): ProjectWorkspaceSummary {
  return {
    id: project.id,
    notebookId: projectIdToNotebookId(project.id),
    name: project.name,
    description: project.description,
    status: project.status,
    createdAt: project.created_at,
    updatedAt: project.updated_at,
    sourceCount: project.source_count,
    noteCount: options?.noteCount ?? null,
    artifactCount: project.artifact_count,
    memoryCount: project.memory_count,
  }
}

function collectSourceStats(sources: SourceListResponse[]) {
  const processingSourceCount = sources.filter((source) =>
    ['new', 'queued', 'running'].includes(source.status || '')
  ).length
  const embeddedSourceCount = sources.filter((source) => source.embedded).length
  const visualReadyCount = sources.filter(
    (source) => source.visual_index_status === 'completed'
  ).length
  const insightCount = sources.reduce(
    (total, source) => total + (source.insights_count || 0),
    0
  )

  return {
    processingSourceCount,
    embeddedSourceCount,
    visualReadyCount,
    insightCount,
  }
}

function buildFallbackKeywords(params: {
  topics: string[]
  embeddedSourceCount: number
  visualReadyCount: number
  sourceCount: number
}) {
  return dedupeStrings([
    ...params.topics,
    params.embeddedSourceCount > 0 ? '文本检索' : null,
    params.visualReadyCount > 0 ? '视觉证据' : null,
    params.sourceCount > 0 ? '项目画像' : null,
  ]).slice(0, 8)
}

function mapTimelineEvents(
  events: ProjectTimelineEventResponse[]
): ProjectTimelineEvent[] {
  return events.map((event) => ({
    id: event.id,
    title: event.title,
    description: event.description,
    occurredAt: event.occurred_at,
    sourceRefs: event.source_refs,
  }))
}

export function buildProjectOverviewViewModel(params: {
  notebook: NotebookResponse
  sources?: SourceListResponse[]
}): ProjectOverviewViewModel {
  const sources = params.sources ?? []
  const project = toProjectWorkspaceSummary(params.notebook)
  const {
    processingSourceCount,
    embeddedSourceCount,
    visualReadyCount,
    insightCount,
  } = collectSourceStats(sources)
  const rawTopics = sources.flatMap((source) => source.topics || [])
  const topics = dedupeStrings(rawTopics).slice(0, 6)
  const effectiveTopics = topics.length > 0 ? topics : DEFAULT_TOPICS
  const keywords = buildFallbackKeywords({
    topics: effectiveTopics,
    embeddedSourceCount,
    visualReadyCount,
    sourceCount: params.notebook.source_count,
  })

  return {
    project,
    sourceCount: project.sourceCount,
    artifactCount: project.artifactCount,
    memoryCount: project.memoryCount,
    topics: effectiveTopics,
    keywords,
    risks: buildRiskList({
      sourceCount: project.sourceCount,
      embeddedSourceCount,
      visualReadyCount,
      processingSourceCount,
    }),
    timelineEvents: buildTimelineEvents({
      projectId: project.id,
      createdAt: params.notebook.created,
      updatedAt: params.notebook.updated,
      sources,
      processingSourceCount,
    }),
    recommendedQuestions: buildRecommendedQuestions(
      effectiveTopics,
      project.sourceCount > 0
    ),
    recentArtifacts: [],
    recentRuns: [],
    stats: {
      noteCount: project.noteCount,
      embeddedSourceCount,
      visualReadyCount,
      insightCount,
    },
  }
}

export function buildProjectOverviewFromResponse(params: {
  overview: ProjectOverviewResponse
  sources?: SourceListResponse[]
  noteCount?: number
}): ProjectOverviewViewModel {
  const sources = params.sources ?? []
  const project = projectSummaryToWorkspaceSummary(params.overview.project, {
    noteCount: params.noteCount,
  })
  const {
    processingSourceCount,
    embeddedSourceCount,
    visualReadyCount,
    insightCount,
  } = collectSourceStats(sources)
  const effectiveTopics =
    params.overview.topics.length > 0 ? params.overview.topics : DEFAULT_TOPICS
  const keywords =
    params.overview.keywords.length > 0
      ? params.overview.keywords
      : buildFallbackKeywords({
          topics: effectiveTopics,
          embeddedSourceCount,
          visualReadyCount,
          sourceCount: params.overview.source_count,
        })

  return {
    project,
    sourceCount: params.overview.source_count,
    artifactCount: params.overview.artifact_count,
    memoryCount: params.overview.memory_count,
    topics: effectiveTopics,
    keywords,
    risks:
      params.overview.risks.length > 0
        ? params.overview.risks
        : buildRiskList({
            sourceCount: params.overview.source_count,
            embeddedSourceCount,
            visualReadyCount,
            processingSourceCount,
          }),
    timelineEvents:
      params.overview.timeline_events.length > 0
        ? mapTimelineEvents(params.overview.timeline_events)
        : buildTimelineEvents({
            projectId: project.id,
            createdAt: params.overview.project.created_at,
            updatedAt: params.overview.project.updated_at,
            sources,
            processingSourceCount,
          }),
    recommendedQuestions:
      params.overview.recommended_questions.length > 0
        ? params.overview.recommended_questions
        : buildRecommendedQuestions(effectiveTopics, params.overview.source_count > 0),
    recentArtifacts: params.overview.recent_artifacts.map((artifact) => ({
      id: artifact.id,
      title: artifact.title,
      artifactType: artifact.artifact_type,
      createdAt: artifact.created_at,
    })),
    recentRuns: params.overview.recent_runs.map((run) => ({
      id: run.id,
      runType: run.run_type,
      status: run.status,
      createdAt: run.created_at,
    })),
    stats: {
      noteCount: params.noteCount ?? null,
      embeddedSourceCount,
      visualReadyCount,
      insightCount,
    },
  }
}
