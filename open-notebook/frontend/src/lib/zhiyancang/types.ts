export type GlobalSection = 'projects' | 'library' | 'system'

export type ProjectSection =
  | 'overview'
  | 'workspace'
  | 'evidence'
  | 'compare'
  | 'memory'
  | 'outputs'
  | 'runs'
  | 'showcase'

export type ProjectPhase = 'collect' | 'ask' | 'compare' | 'memory' | 'outputs' | 'runs'

export type RunStatus = 'queued' | 'running' | 'completed' | 'failed'

export type EvidenceType = 'docs' | 'web' | 'images' | 'audio' | 'visual'

export type SearchMode = 'keyword' | 'semantic' | 'hybrid' | 'rrf'

export type MemoryBucket = 'inbox' | 'stable' | 'frozen' | 'decayed'

export interface PhaseMeta {
  id: ProjectPhase
  label: string
  accent: string
}

export const PROJECT_PHASES: PhaseMeta[] = [
  { id: 'collect', label: 'Collect', accent: 'rgba(71, 182, 255, 0.9)' },
  { id: 'ask', label: 'Ask', accent: 'rgba(71, 182, 255, 0.9)' },
  { id: 'compare', label: 'Compare', accent: 'rgba(240, 174, 67, 0.95)' },
  { id: 'memory', label: 'Memory', accent: 'rgba(159, 113, 255, 0.95)' },
  { id: 'outputs', label: 'Outputs', accent: 'rgba(83, 194, 123, 0.95)' },
  { id: 'runs', label: 'Runs', accent: 'rgba(138, 143, 152, 0.95)' },
]

export function getPhaseMeta(phase: ProjectPhase) {
  return PROJECT_PHASES.find((item) => item.id === phase) ?? PROJECT_PHASES[0]
}

export interface ZycProjectCard {
  id: string
  name: string
  summary: string
  objective: string
  phase: ProjectPhase
  evidenceCount: number
  memoryCount: number
  latestOutput: string
  runStatus: string
  updatedAt: string
  owner: string
  heroImage: string
  badge: string
}

export interface ZycOverviewRailItem {
  id: string
  title: string
  meta: string
  detail: string
}

export interface ZycOverviewModel {
  goal: string
  keyQuestions: string[]
  currentConclusion: string
  riskAlerts: string[]
  nextSteps: string[]
  recentEvidence: ZycOverviewRailItem[]
  recentMemory: ZycOverviewRailItem[]
  recentRuns: ZycOverviewRailItem[]
  artifacts: ZycOverviewRailItem[]
}

export interface ZycWorkspaceTask {
  id: string
  title: string
  status: 'todo' | 'active' | 'done'
}

export interface ZycPinnedEvidence {
  id: string
  title: string
  source: string
}

export interface ZycToolToggle {
  id: string
  label: string
  description: string
  enabled: boolean
}

export interface ZycAgentCard {
  id: 'researcher' | 'retriever' | 'visual' | 'synthesizer'
  title: string
  status: 'idle' | 'active' | 'watching' | 'ready'
  taskInput: string
  plan: string[]
  result: string
}

export interface ZycCitation {
  id: string
  label: string
  source: string
  page: string
}

export interface ZycWorkspaceLog {
  id: string
  time: string
  text: string
}

export interface ZycWorkspaceModel {
  tasks: ZycWorkspaceTask[]
  pinnedEvidence: ZycPinnedEvidence[]
  retrievalModes: SearchMode[]
  memoryScopes: string[]
  toolToggles: ZycToolToggle[]
  agents: ZycAgentCard[]
  citations: ZycCitation[]
  runTrace: string[]
  keyLogs: ZycWorkspaceLog[]
}

export interface ZycEvidenceItem {
  id: string
  type: EvidenceType
  title: string
  source: string
  snippet: string
  thumbnail: string
  confidence: string
  actions: string[]
}

export interface ZycEvidenceModel {
  items: ZycEvidenceItem[]
  searchModes: SearchMode[]
}

export interface ZycCompareResultGroup {
  id: string
  title: string
  accent: string
  items: string[]
}

export interface ZycCompareModel {
  sources: Array<{ id: string; label: string }>
  status: RunStatus
  results: ZycCompareResultGroup[]
}

export interface ZycMemoryItem {
  id: string
  bucket: MemoryBucket
  content: string
  source: string
  confidence: number
  scope: string
  status: string
  decay: number[]
}

export interface ZycOutputVersion {
  id: string
  label: string
  status: string
  generatedAt: string
}

export interface ZycOutputItem {
  id: string
  title: string
  template: string
  status: string
  preview: string
  versions: ZycOutputVersion[]
}

export interface ZycRunStep {
  id: string
  title: string
  status: string
  detail: string
  code?: string
}

export interface ZycRunModel {
  id: string
  goal: string
  agentUsed: string
  evidenceReferenced: string[]
  toolsInvoked: string[]
  stateTimeline: ZycRunStep[]
  finalOutput: string
  exceptions: string[]
  screenshots: Array<{ id: string; label: string; image: string }>
}

export interface ZycLibraryModel {
  categories: Array<{
    id: EvidenceType
    title: string
    description: string
    count: number
    image: string
    href: string
  }>
  recent: Array<{
    id: string
    title: string
    type: string
    source: string
    updatedAt: string
  }>
}

export interface ZycSystemModel {
  cards: Array<{
    id: string
    title: string
    description: string
    health: string
    href: string
  }>
  health: Array<{
    id: string
    label: string
    value: string
  }>
}

export interface ZycProjectRecord {
  project: ZycProjectCard
  overview: ZycOverviewModel
  workspace: ZycWorkspaceModel
  evidence: ZycEvidenceModel
  compare: ZycCompareModel
  memory: ZycMemoryItem[]
  outputs: ZycOutputItem[]
  runs: ZycRunModel[]
}
