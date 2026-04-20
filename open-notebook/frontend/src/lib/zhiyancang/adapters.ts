import type {
  AgentRunResponse,
  ArtifactRecordResponse,
  EvidenceCardResponse,
  EvidenceThreadDetailResponse,
  EvidenceThreadSummaryResponse,
  MemoryRecordResponse,
  ProjectCompareRecordResponse,
  ProjectOverviewResponse,
  ProjectSummaryResponse,
  SettingsResponse,
  SourceListResponse,
  CommandJobListItemResponse,
} from '@/lib/types/api'
import type { CredentialStatus } from '@/lib/api/credentials'
import type { Model, ModelDefaults } from '@/lib/types/models'
import { formatProjectTimestamp } from '@/lib/project-workspace'

import type {
  EvidenceType,
  MemoryBucket,
  ProjectPhase,
  RunStatus,
  SearchMode,
  ZycAgentCard,
  ZycCompareModel,
  ZycCompareResultGroup,
  ZycEvidenceItem,
  ZycEvidenceModel,
  ZycLibraryModel,
  ZycMemoryItem,
  ZycOutputItem,
  ZycOutputVersion,
  ZycOverviewModel,
  ZycOverviewRailItem,
  ZycPinnedEvidence,
  ZycProjectCard,
  ZycProjectRecord,
  ZycRunModel,
  ZycRunStep,
  ZycSystemModel,
  ZycWorkspaceLog,
  ZycWorkspaceModel,
  ZycWorkspaceTask,
} from './types'

const HERO_IMAGES = [
  'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80',
  'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1200&q=80',
]

const LIBRARY_IMAGES: Record<EvidenceType, string> = {
  docs:
    'https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=1200&q=80',
  web:
    'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1200&q=80',
  images:
    'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80',
  audio:
    'https://images.unsplash.com/photo-1511379938547-c1f69419868d?auto=format&fit=crop&w=1200&q=80',
  visual:
    'https://images.unsplash.com/photo-1516321497487-e288fb19713f?auto=format&fit=crop&w=1200&q=80',
}

const EVIDENCE_PLACEHOLDERS: Record<EvidenceType, string> = {
  docs:
    'https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=1200&q=80',
  web:
    'https://images.unsplash.com/photo-1516321497487-e288fb19713f?auto=format&fit=crop&w=1200&q=80',
  images:
    'https://images.unsplash.com/photo-1493246507139-91e8fad9978e?auto=format&fit=crop&w=1200&q=80',
  audio:
    'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?auto=format&fit=crop&w=1200&q=80',
  visual:
    'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80',
}

const RETRIEVAL_MODES: SearchMode[] = ['keyword', 'semantic', 'hybrid', 'rrf']
const MEMORY_SCOPES = ['Project Memory', 'User Memory']

const ARTIFACT_TEMPLATE_LABELS: Record<string, string> = {
  project_summary: 'Project Summary',
  defense_outline: 'Defense Pitch',
  diff_report: 'Competition Brief',
  judge_questions: 'Judge Questions',
  qa_cards: 'QA Cards',
  literature_review: 'Literature Review',
  risk_list: 'Risk List',
  presentation_script: 'Presentation Script',
  podcast: 'Podcast',
}

function stableIndex(value: string, size: number) {
  let hash = 0
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0
  }
  return size > 0 ? hash % size : 0
}

function truncate(value: string | null | undefined, limit = 180) {
  const normalized = (value || '').trim()
  if (!normalized) {
    return ''
  }
  if (normalized.length <= limit) {
    return normalized
  }
  return `${normalized.slice(0, limit - 1)}...`
}

function extractExtension(source?: SourceListResponse | null) {
  const path = source?.asset?.file_path || source?.asset?.url || ''
  const match = path.toLowerCase().match(/\.([a-z0-9]+)(?:$|\?)/)
  return match?.[1] || ''
}

function isVisualReady(source?: SourceListResponse | null) {
  return source?.visual_index_status === 'completed' || (source?.visual_asset_count || 0) > 0
}

export function categorizeSource(source: SourceListResponse): EvidenceType {
  const extension = extractExtension(source)
  const url = (source.asset?.url || '').toLowerCase()

  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'].includes(extension)) {
    return 'images'
  }

  if (['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac'].includes(extension)) {
    return 'audio'
  }

  if (!source.asset?.file_path && source.asset?.url) {
    return 'web'
  }

  if (isVisualReady(source) && ['pdf', 'ppt', 'pptx', 'doc', 'docx'].includes(extension || 'pdf')) {
    return 'visual'
  }

  if (url.includes('youtube.com') || url.includes('youtu.be') || ['mp4', 'mov'].includes(extension)) {
    return 'visual'
  }

  return 'docs'
}

function mapPhase(project: ProjectSummaryResponse): ProjectPhase {
  return project.phase || 'collect'
}

function mapRunStatus(status?: string | null) {
  return status || 'idle'
}

function mapOutputStatus(status?: string | null) {
  if (status === 'ready') {
    return 'completed'
  }
  if (status === 'draft') {
    return 'completed'
  }
  return status || 'completed'
}

function mapCompareStatus(status?: string | null): RunStatus {
  if (status === 'queued' || status === 'running' || status === 'completed' || status === 'failed') {
    return status
  }
  return 'completed'
}

function buildProjectBadge(project: ProjectSummaryResponse) {
  if (project.status === 'archived') {
    return 'Archived'
  }
  return project.source_count > 0 ? 'Research' : 'New Project'
}

export function mapProjectSummaryToZycProjectCard(project: ProjectSummaryResponse): ZycProjectCard {
  const latestOutput = project.latest_output_title || 'No output yet'
  return {
    id: project.id,
    name: project.name,
    summary:
      truncate(project.description, 120) ||
      'Build a clean evidence line, keep the thread stable, then turn it into outputs.',
    objective:
      truncate(project.description, 160) ||
      'Organize evidence, compare claims, keep durable memory, and ship reusable outputs.',
    phase: mapPhase(project),
    evidenceCount: project.source_count,
    memoryCount: project.memory_count,
    latestOutput,
    runStatus: mapRunStatus(project.latest_run_status),
    updatedAt: formatProjectTimestamp(project.updated_at),
    owner: 'ZhiyanCang',
    heroImage: HERO_IMAGES[stableIndex(project.id, HERO_IMAGES.length)],
    badge: buildProjectBadge(project),
  }
}

function buildOverviewGoal(overview: ProjectOverviewResponse) {
  return (
    truncate(overview.project.description, 220) ||
    `围绕 ${overview.project.name} 的核心资料、证据链和输出路径，形成可继续推进的研究主线。`
  )
}

function buildCurrentConclusion(overview: ProjectOverviewResponse) {
  if (overview.topics.length > 0) {
    return `当前主线集中在 ${overview.topics.slice(0, 3).join(' / ')}，已接入 ${overview.source_count} 份资料，可继续围绕风险和推荐问题推进。`
  }

  if (overview.project.description) {
    return truncate(overview.project.description, 200)
  }

  return '当前还在整理项目主线，适合先补齐关键资料，再进入证据问答和产物生成。'
}

function buildNextSteps(overview: ProjectOverviewResponse) {
  const steps = [
    ...overview.recommended_questions.map((question) => `围绕“${question}”继续追问并固化证据。`),
  ]

  if (overview.recent_artifacts.length === 0) {
    steps.push('基于当前总览生成第一版项目综述或答辩提纲。')
  }

  return steps.slice(0, 4)
}

function railItem(id: string, title: string, meta: string, detail: string): ZycOverviewRailItem {
  return {
    id,
    title,
    meta,
    detail,
  }
}

export function mapOverviewModel(params: {
  overview: ProjectOverviewResponse
  thread?: EvidenceThreadDetailResponse | null
  memories?: MemoryRecordResponse[]
}): ZycOverviewModel {
  const { overview, thread, memories = [] } = params
  const evidenceItems =
    thread?.latest_response?.evidence_cards.slice(0, 4).map((card, index) =>
      railItem(
        card.id || `${card.source_id}-${index}`,
        card.source_name,
        card.citation_text || 'Evidence',
        truncate(card.excerpt, 110)
      )
    ) || []

  const memoryItems = memories.slice(0, 4).map((memory) =>
    railItem(
      memory.id,
      truncate(memory.text, 60),
      `${memory.status} · ${memory.scope}`,
      `${Math.round(memory.confidence * 100)}% confidence`
    )
  )

  const runItems = overview.recent_runs.map((run) =>
    railItem(
      run.id,
      run.run_type,
      run.status,
      formatProjectTimestamp(run.completed_at || run.created_at)
    )
  )

  const artifactItems = overview.recent_artifacts.map((artifact) =>
    railItem(
      artifact.id,
      artifact.title,
      artifact.artifact_type,
      formatProjectTimestamp(artifact.created_at)
    )
  )

  return {
    goal: buildOverviewGoal(overview),
    keyQuestions:
      overview.recommended_questions.slice(0, 4).length > 0
        ? overview.recommended_questions.slice(0, 4)
        : ['这个项目最关键的证据链还缺哪一块？'],
    currentConclusion: buildCurrentConclusion(overview),
    riskAlerts: overview.risks.length > 0 ? overview.risks : ['当前还没有足够的风险信号。'],
    nextSteps: buildNextSteps(overview),
    recentEvidence: evidenceItems,
    recentMemory: memoryItems,
    recentRuns: runItems,
    artifacts: artifactItems,
  }
}

function buildEvidenceItem(
  card: EvidenceCardResponse,
  sourceById: Map<string, SourceListResponse>
): ZycEvidenceItem {
  const source = sourceById.get(card.source_id)
  const primaryType = card.image_thumb
    ? 'images'
    : source
      ? categorizeSource(source)
      : 'docs'

  return {
    id: card.id || `${card.source_id}:${card.internal_ref}`,
    type: primaryType,
    title: card.source_name,
    source: card.citation_text || source?.title || card.source_id,
    snippet: truncate(card.excerpt || card.relevance_reason || '', 180),
    thumbnail: card.image_thumb || EVIDENCE_PLACEHOLDERS[primaryType],
    confidence:
      typeof card.score === 'number' ? `${Math.round(card.score * 100)}% match` : 'evidence',
    actions: ['Open Source', 'Trace'],
  }
}

export function mapEvidenceModel(params: {
  thread?: EvidenceThreadDetailResponse | null
  sources?: SourceListResponse[]
}): ZycEvidenceModel {
  const { thread, sources = [] } = params
  const sourceById = new Map(sources.map((source) => [source.id, source]))
  const items =
    thread?.latest_response?.evidence_cards.map((card) => buildEvidenceItem(card, sourceById)) || []

  return {
    items,
    searchModes: RETRIEVAL_MODES,
  }
}

function buildWorkspaceTasks(overview: ProjectOverviewResponse): ZycWorkspaceTask[] {
  return [
    ...overview.recommended_questions.slice(0, 3).map((question, index) => {
      const status: ZycWorkspaceTask['status'] = index === 0 ? 'active' : 'todo'
      return {
        id: `question:${index}`,
        title: question,
        status,
      }
    }),
    ...overview.risks.slice(0, 2).map((risk, index) => {
      const status: ZycWorkspaceTask['status'] = 'todo'
      return {
        id: `risk:${index}`,
        title: risk,
        status,
      }
    }),
  ]
}

function buildPinnedEvidence(
  thread?: EvidenceThreadDetailResponse | null
): ZycPinnedEvidence[] {
  return (
    thread?.latest_response?.evidence_cards.slice(0, 5).map((card, index) => ({
      id: card.id || `${card.source_id}:${index}`,
      title: truncate(card.excerpt, 80) || card.source_name,
      source: card.citation_text || card.source_name,
    })) || []
  )
}

function buildWorkspaceAgents(params: {
  thread?: EvidenceThreadDetailResponse | null
  latestRun?: AgentRunResponse | null
}): ZycAgentCard[] {
  const { thread, latestRun } = params
  const question = thread?.last_question || latestRun?.input_summary || 'No active question yet'
  const answer = thread?.latest_response?.answer || 'Waiting for the next grounded answer.'
  const steps = latestRun?.steps || []
  const toolCalls = latestRun?.tool_calls || []

  return [
    {
      id: 'researcher',
      title: 'Researcher',
      status: latestRun ? 'active' : 'idle',
      taskInput: question,
      plan: steps.slice(0, 3).map((step) => step.title),
      result: truncate(answer, 140) || 'Use the latest thread to structure the next answer.',
    },
    {
      id: 'retriever',
      title: 'Retriever',
      status: thread?.latest_response?.evidence_cards.length ? 'ready' : 'watching',
      taskInput: `${thread?.latest_response?.evidence_cards.length || 0} evidence cards`,
      plan:
        thread?.latest_response?.evidence_cards.slice(0, 3).map((card) => card.source_name) || [],
      result:
        thread?.latest_response?.evidence_cards[0]?.citation_text ||
        'No evidence pinned to the current workspace yet.',
    },
    {
      id: 'visual',
      title: 'Visual',
      status: thread?.latest_response?.mode === 'visual' || thread?.latest_response?.mode === 'mixed' ? 'active' : 'watching',
      taskInput: thread?.latest_response?.mode || 'text',
      plan: ['Check page-anchored references', 'Watch visual retrieval results'],
      result:
        thread?.latest_response?.evidence_cards.find((card) => card.image_thumb)?.citation_text ||
        'No visual evidence in the active thread.',
    },
    {
      id: 'synthesizer',
      title: 'Synthesizer',
      status: latestRun?.status === 'completed' ? 'ready' : latestRun ? 'active' : 'idle',
      taskInput: latestRun?.run_type || 'No run',
      plan: toolCalls.slice(0, 3),
      result:
        truncate(
          typeof latestRun?.output_json?.summary === 'string'
            ? latestRun.output_json.summary
            : answer,
          140
        ) || 'No synthesized output yet.',
    },
  ]
}

function buildWorkspaceLogs(latestRun?: AgentRunResponse | null): ZycWorkspaceLog[] {
  return (
    latestRun?.steps.slice(0, 6).map((step) => ({
      id: step.id,
      time: formatProjectTimestamp(step.completed_at || step.started_at || latestRun.created_at),
      text: truncate(step.error || step.title, 160) || step.title,
    })) || []
  )
}

export function mapWorkspaceModel(params: {
  overview: ProjectOverviewResponse
  thread?: EvidenceThreadDetailResponse | null
  latestRun?: AgentRunResponse | null
}): ZycWorkspaceModel {
  const { overview, thread, latestRun } = params

  return {
    tasks: buildWorkspaceTasks(overview),
    pinnedEvidence: buildPinnedEvidence(thread),
    retrievalModes: RETRIEVAL_MODES,
    memoryScopes: MEMORY_SCOPES,
    toolToggles: [
      {
        id: 'visual-retrieval',
        label: 'Visual Retrieval',
        description: 'Include visual indexing results when the thread needs screenshots or figures.',
        enabled: thread?.latest_response?.mode === 'visual' || thread?.latest_response?.mode === 'mixed',
      },
      {
        id: 'memory-writeback',
        label: 'Memory Writeback',
        description: 'Let accepted answers turn into reviewable project memory.',
        enabled: Boolean(thread?.latest_response?.memory_updates.length),
      },
      {
        id: 'artifact-ready',
        label: 'Artifact Ready',
        description: 'Keep the current thread reusable for markdown artifact generation.',
        enabled: Boolean(thread?.latest_response?.answer),
      },
    ],
    agents: buildWorkspaceAgents({ thread, latestRun }),
    citations:
      thread?.latest_response?.evidence_cards.slice(0, 5).map((card, index) => ({
        id: card.id || `${card.source_id}:${index}`,
        label: card.source_name,
        source: card.citation_text || card.source_id,
        page: card.page_no ? `p.${card.page_no}` : 'source',
      })) || [],
    runTrace: latestRun?.steps.map((step) => step.title) || [],
    keyLogs: buildWorkspaceLogs(latestRun),
  }
}

export function mapCompareModel(params: {
  sources: SourceListResponse[]
  compares: ProjectCompareRecordResponse[]
}): ZycCompareModel {
  const { sources, compares } = params
  const latestCompare = compares[0]
  const result = latestCompare?.result

  const groups: ZycCompareResultGroup[] = [
    {
      id: 'similarities',
      title: 'Similarities',
      accent: 'rgba(240, 174, 67, 0.95)',
      items: result?.similarities.map((item) => item.detail) || [],
    },
    {
      id: 'differences',
      title: 'Differences',
      accent: 'rgba(240, 174, 67, 0.75)',
      items: result?.differences.map((item) => item.detail) || [],
    },
    {
      id: 'conflicts',
      title: 'Conflicts',
      accent: 'rgba(240, 174, 67, 0.65)',
      items: result?.conflicts.map((item) => item.detail) || [],
    },
    {
      id: 'missing',
      title: 'Missing Items',
      accent: 'rgba(240, 174, 67, 0.55)',
      items: result?.missing_items.map((item) => item.detail) || [],
    },
  ]

  return {
    sources: sources.map((source) => ({
      id: source.id,
      label: source.title || source.id,
    })),
    status: mapCompareStatus(latestCompare?.status),
    results: groups,
  }
}

function memoryBucketFromStatus(status: MemoryRecordResponse['status']): MemoryBucket {
  if (status === 'accepted') {
    return 'stable'
  }
  if (status === 'frozen') {
    return 'frozen'
  }
  if (status === 'deprecated') {
    return 'decayed'
  }
  return 'inbox'
}

function buildDecayCurve(confidence: number, status: MemoryRecordResponse['status']) {
  const base = Math.max(0.1, Math.min(1, confidence))
  if (status !== 'deprecated') {
    return [base, base, base, base, base]
  }
  return [base, base * 0.86, base * 0.66, base * 0.44, base * 0.22].map((value) =>
    Number(value.toFixed(3))
  )
}

export function mapMemoryItems(memories: MemoryRecordResponse[]): ZycMemoryItem[] {
  return memories.map((memory) => ({
    id: memory.id,
    bucket: memoryBucketFromStatus(memory.status),
    content: memory.text,
    source:
      memory.source_refs[0]?.citation_text ||
      memory.source_refs[0]?.source_name ||
      memory.source_refs[0]?.source_id ||
      'No source',
    confidence: memory.confidence,
    scope: memory.scope,
    status: memory.status,
    decay: buildDecayCurve(memory.confidence, memory.status),
  }))
}

function artifactTemplateLabel(artifact: ArtifactRecordResponse) {
  const normalizedTitle = artifact.title.toLowerCase()

  if (artifact.artifact_type === 'project_summary' && normalizedTitle.includes('poster')) {
    return 'Poster Copy'
  }
  if (artifact.artifact_type === 'defense_outline' && normalizedTitle.includes('ppt')) {
    return 'PPT Outline'
  }

  return ARTIFACT_TEMPLATE_LABELS[artifact.artifact_type] || artifact.title
}

function artifactVersionGroupKey(artifact: ArtifactRecordResponse) {
  return artifact.title || artifactTemplateLabel(artifact)
}

function buildOutputPreview(artifact: ArtifactRecordResponse) {
  return truncate(artifact.content_md, 220) || 'Queued artifact. Content will appear here after generation.'
}

export function mapOutputItems(artifacts: ArtifactRecordResponse[]): ZycOutputItem[] {
  const groups = new Map<string, ArtifactRecordResponse[]>()

  artifacts.forEach((artifact) => {
    const key = artifactVersionGroupKey(artifact)
    const bucket = groups.get(key) || []
    bucket.push(artifact)
    groups.set(key, bucket)
  })

  return [...groups.entries()].map(([key, versions]) => {
    const sortedVersions = [...versions].sort((left, right) =>
      right.updated_at.localeCompare(left.updated_at)
    )
    const latest = sortedVersions[0]
    const mappedVersions: ZycOutputVersion[] = sortedVersions.map((artifact, index) => ({
      id: artifact.id,
      label: index === 0 ? 'Latest' : `Version ${sortedVersions.length - index}`,
      status: mapOutputStatus(artifact.status),
      generatedAt: formatProjectTimestamp(artifact.updated_at),
    }))

    return {
      id: latest.id,
      title: key,
      template: artifactTemplateLabel(latest),
      status: mapOutputStatus(latest.status),
      preview: buildOutputPreview(latest),
      versions: mappedVersions,
    }
  })
}

function formatStepDetail(step: AgentRunResponse['steps'][number]) {
  if (step.error) {
    return step.error
  }
  if (step.tool_name) {
    return `${step.tool_name}${step.output_refs.length ? ` -> ${step.output_refs.join(', ')}` : ''}`
  }
  if (step.evidence_refs.length > 0) {
    return `Evidence: ${step.evidence_refs.slice(0, 3).join(', ')}`
  }
  if (step.output_refs.length > 0) {
    return `Outputs: ${step.output_refs.slice(0, 3).join(', ')}`
  }
  return step.title
}

function formatCodeBlock(step: AgentRunResponse['steps'][number]) {
  const payload: Record<string, unknown> = {}
  if (step.input_json) {
    payload.input = step.input_json
  }
  if (step.output_json) {
    payload.output = step.output_json
  }
  if (step.error) {
    payload.error = step.error
  }

  if (Object.keys(payload).length === 0) {
    return undefined
  }

  return JSON.stringify(payload, null, 2)
}

export function mapRunModels(runs: AgentRunResponse[]): ZycRunModel[] {
  return runs.map((run) => {
    const steps: ZycRunStep[] = run.steps.map((step) => ({
      id: step.id,
      title: step.title,
      status: step.status,
      detail: formatStepDetail(step),
      code: formatCodeBlock(step),
    }))

    const exceptions = [
      ...(run.failure_reason ? [run.failure_reason] : []),
      ...run.steps.flatMap((step) => (step.error ? [step.error] : [])),
    ]

    const finalOutput =
      truncate(
        typeof run.output_json?.answer === 'string'
          ? run.output_json.answer
          : typeof run.output_json?.summary === 'string'
            ? run.output_json.summary
            : '',
        320
      ) ||
      (run.outputs.length > 0
        ? `Outputs: ${run.outputs.join(', ')}`
        : `${run.run_type} run ${run.status}`)

    return {
      id: run.id,
      goal: run.input_summary || `Run ${run.run_type}`,
      agentUsed: run.selected_skill || 'project_harness',
      evidenceReferenced: run.evidence_reads,
      toolsInvoked: run.tool_calls,
      stateTimeline: steps,
      finalOutput,
      exceptions,
      screenshots: [],
    }
  })
}

export function buildZycProjectRecord(params: {
  overview: ProjectOverviewResponse
  threads: EvidenceThreadSummaryResponse[]
  thread?: EvidenceThreadDetailResponse | null
  sources: SourceListResponse[]
  compares: ProjectCompareRecordResponse[]
  memories: MemoryRecordResponse[]
  artifacts: ArtifactRecordResponse[]
  runs: AgentRunResponse[]
}): ZycProjectRecord {
  const {
    overview,
    threads,
    thread,
    sources,
    compares,
    memories,
    artifacts,
    runs,
  } = params
  const project = mapProjectSummaryToZycProjectCard(overview.project)
  const latestThreadId = thread?.id || threads[0]?.id
  const activeThread =
    thread && latestThreadId && thread.id === latestThreadId ? thread : thread || null
  const latestRun = runs[0] || null

  return {
    project,
    overview: mapOverviewModel({ overview, thread: activeThread, memories }),
    workspace: mapWorkspaceModel({
      overview,
      thread: activeThread,
      latestRun,
    }),
    evidence: mapEvidenceModel({ thread: activeThread, sources }),
    compare: mapCompareModel({ sources, compares }),
    memory: mapMemoryItems(memories),
    outputs: mapOutputItems(artifacts),
    runs: mapRunModels(runs),
  }
}

export function mapLibraryModel(sources: SourceListResponse[]): ZycLibraryModel {
  const categories: ZycLibraryModel['categories'] = [
    {
      id: 'docs',
      title: 'Docs',
      description: 'Structured project documents, PDFs, and slide decks.',
      count: sources.filter((source) => categorizeSource(source) === 'docs').length,
      image: LIBRARY_IMAGES.docs,
      href: '/sources',
    },
    {
      id: 'web',
      title: 'Web',
      description: 'Web pages and URL-based research material linked into projects.',
      count: sources.filter((source) => categorizeSource(source) === 'web').length,
      image: LIBRARY_IMAGES.web,
      href: '/sources',
    },
    {
      id: 'images',
      title: 'Images',
      description: 'Image-based assets and screenshot-ready material.',
      count: sources.filter((source) => categorizeSource(source) === 'images').length,
      image: LIBRARY_IMAGES.images,
      href: '/sources',
    },
    {
      id: 'audio',
      title: 'Audio',
      description: 'Speech, audio references, and multimodal inputs.',
      count: sources.filter((source) => categorizeSource(source) === 'audio').length,
      image: LIBRARY_IMAGES.audio,
      href: '/sources',
    },
    {
      id: 'visual',
      title: 'Visual Evidence',
      description: 'Sources with completed visual indexing and retrieval support.',
      count: sources.filter((source) => isVisualReady(source)).length,
      image: LIBRARY_IMAGES.visual,
      href: '/vrag',
    },
  ]

  return {
    categories,
    recent: sources.slice(0, 6).map((source) => ({
      id: source.id,
      title: source.title || source.id,
      type: categorizeSource(source),
      source: source.asset?.url || source.asset?.file_path || 'local',
      updatedAt: formatProjectTimestamp(source.updated),
    })),
  }
}

function settingsHealth(settings?: SettingsResponse | null) {
  const configured = [
    settings?.default_content_processing_engine_doc,
    settings?.default_content_processing_engine_url,
    settings?.default_embedding_option,
  ].filter(Boolean).length
  return configured >= 2 ? 'Configured' : 'Needs Setup'
}

export function mapSystemModel(params: {
  models: Model[]
  defaults?: ModelDefaults | null
  settings?: SettingsResponse | null
  jobs: CommandJobListItemResponse[]
  evalJobs: CommandJobListItemResponse[]
  credentials?: CredentialStatus | null
}): ZycSystemModel {
  const { models, defaults, settings, jobs, evalJobs, credentials } = params
  const activeJobs = jobs.filter((job) => job.status === 'queued' || job.status === 'running')
  const configuredProviders = credentials
    ? Object.values(credentials.configured).filter(Boolean).length
    : 0

  return {
    cards: [
      {
        id: 'models',
        title: 'Models',
        description: 'Registered models, providers, and default slots.',
        health: `${models.length} registered`,
        href: '/models',
      },
      {
        id: 'settings',
        title: 'Settings',
        description: 'Core runtime switches and default research configuration.',
        health: settingsHealth(settings),
        href: '/settings',
      },
      {
        id: 'jobs',
        title: 'Jobs',
        description: 'Queued and running commands across the research control plane.',
        health: activeJobs.length > 0 ? `${activeJobs.length} active` : 'Idle',
        href: '/admin/jobs',
      },
      {
        id: 'evals',
        title: 'Evals',
        description: 'Project evaluation runs and recent scoring jobs.',
        health: evalJobs.length > 0 ? `${evalJobs.length} recent` : 'No runs yet',
        href: '/admin/evals',
      },
    ],
    health: [
      {
        id: 'providers',
        label: 'Providers',
        value: `${configuredProviders} configured`,
      },
      {
        id: 'defaults',
        label: 'Default Models',
        value: `${Object.values(defaults || {}).filter(Boolean).length} slots`,
      },
      {
        id: 'jobs',
        label: 'Active Jobs',
        value: `${activeJobs.length}`,
      },
      {
        id: 'encryption',
        label: 'Credential Vault',
        value: credentials?.encryption_configured ? 'Enabled' : 'Not Ready',
      },
    ],
  }
}
