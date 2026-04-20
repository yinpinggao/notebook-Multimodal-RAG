import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LibraryPage from './library/page'
import SystemPage from './system/page'
import ProjectsPage from './projects/page'
import ProjectComparePage from './projects/[projectId]/compare/page'
import ProjectEvidencePage from './projects/[projectId]/evidence/page'
import ProjectMemoryPage from './projects/[projectId]/memory/page'
import ProjectOutputsPage from './projects/[projectId]/outputs/page'
import ProjectOverviewPage from './projects/[projectId]/overview/page'
import ProjectRunsPage from './projects/[projectId]/runs/page'
import ProjectShowcasePage from './projects/[projectId]/showcase/page'
import ProjectWorkspacePage from './projects/[projectId]/workspace/page'
import { zycLibraryModel, zycProjects, zycSystemModel } from '@/lib/zhiyancang/mock-data'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import { mockUseParams, mockUsePathname } from '@/test/setup'

const detailMock = {
  data: zycProjects[0],
  isLoading: false,
  error: null,
  meta: {
    overview: {
      project: { name: zycProjects[0].project.name },
      recommended_questions: zycProjects[0].overview.keyQuestions,
    },
    threads: [
      {
        id: 'thread-1',
        title: 'Why this project matters',
        updated_at: '2026-04-20T10:00:00Z',
        message_count: 2,
        last_question: 'What is the strongest evidence?',
      },
    ],
    activeThreadId: 'thread-1',
    activeThread: {
      id: 'thread-1',
      title: 'Why this project matters',
      latest_response: {
        answer: 'Grounded answer',
        suggested_followups: ['Follow up'],
      },
    },
    sources: [
      { id: 'source:1', title: 'Source A' },
      { id: 'source:2', title: 'Source B' },
    ],
    compares: [{ id: 'compare:1', result: { summary: 'Latest compare summary' } }],
    memories: [{ id: 'memory:1', scope: 'project', text: 'Memory text' }],
    artifacts: [{ id: 'artifact:1' }],
    runs: [],
  },
}

vi.mock('@/lib/hooks/use-zyc-projects', () => ({
  useZycProjects: () => ({
    data: {
      projects: zycProjects.map((record) => record.project),
      latestProjectId: zycProjects[0].project.id,
    },
    isLoading: false,
    error: null,
  }),
}))

vi.mock('@/lib/hooks/use-zyc-project-detail', () => ({
  useZycProjectDetail: () => detailMock,
}))

vi.mock('@/lib/hooks/use-zyc-global', () => ({
  useZycLibrary: () => ({
    data: zycLibraryModel,
    isLoading: false,
    error: null,
  }),
  useZycSystem: () => ({
    data: zycSystemModel,
    isLoading: false,
    error: null,
  }),
}))

vi.mock('@/lib/hooks/use-media-query', () => ({
  useMediaQuery: (query: string) => query.includes('min-width'),
}))

vi.mock('@/lib/hooks/use-project-evidence', () => ({
  useAskProject: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
  useFollowupProjectThread: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
}))

vi.mock('@/lib/hooks/use-project-memory', () => ({
  useUpdateProjectMemory: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
  useDeleteProjectMemory: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
  useRebuildProjectMemory: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
  useCreateProjectMemory: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
}))

vi.mock('@/lib/hooks/use-project-artifacts', () => ({
  useCreateProjectArtifact: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
  useRegenerateProjectArtifact: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
  useProjectArtifact: () => ({ data: null, error: null }),
}))

vi.mock('@/lib/hooks/use-project-compare', () => ({
  useCreateProjectCompare: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
  useExportProjectCompare: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
}))

function setProjectRoute(path: string) {
  mockUseParams.mockReturnValue({
    projectId: zycProjects[0].project.id,
    threadId: 'thread-1',
  })
  mockUsePathname.mockReturnValue(path)
  useZycUIStore.setState({
    activeGlobalSection: 'projects',
    activeProjectSection: 'overview',
    mobileNavOpen: false,
    workspaceLeftOpen: false,
    workspaceRightOpen: false,
    evidenceFilterOpen: false,
    outputHistoryOpen: false,
    demoMode: false,
    activeEvidenceType: 'docs',
    activeSearchMode: 'hybrid',
    selectedCompareSourceA: '',
    selectedCompareSourceB: '',
    selectedOutputTemplate: 'Defense Pitch',
    selectedOutputVersionId: 'v1',
    workspaceRetrievalMode: 'hybrid',
    workspaceMemoryScope: 'Project Memory',
  })
}

describe('ZhiyanCang route smoke', () => {
  beforeEach(() => {
    setProjectRoute('/projects')
  })

  it('renders /projects', () => {
    render(<ProjectsPage />)
    expect(screen.getByText('ZhiyanCang')).toBeInTheDocument()
    expect(screen.getByText('Active Research Tracks')).toBeInTheDocument()
  })

  it('renders /library', () => {
    render(<LibraryPage />)
    expect(screen.getByText('Recent Resources')).toBeInTheDocument()
    expect(screen.getAllByText('Docs').length).toBeGreaterThan(0)
  })

  it('renders /system', () => {
    render(<SystemPage />)
    expect(screen.getByText('System Health')).toBeInTheDocument()
    expect(screen.getByText('Models')).toBeInTheDocument()
  })

  it('renders /projects/[id]/overview', () => {
    setProjectRoute(`/projects/${zycProjects[0].project.id}/overview`)
    render(<ProjectOverviewPage />)
    expect(screen.getByText('Project Goal')).toBeInTheDocument()
    expect(screen.getByText('Recent Signals')).toBeInTheDocument()
  })

  it('renders /projects/[id]/workspace', () => {
    setProjectRoute(`/projects/${zycProjects[0].project.id}/workspace`)
    render(<ProjectWorkspacePage />)
    expect(screen.getByText('Researcher')).toBeInTheDocument()
    expect(screen.getByText('Tool Switches')).toBeInTheDocument()
  })

  it('renders /projects/[id]/evidence', () => {
    setProjectRoute(`/projects/${zycProjects[0].project.id}/evidence`)
    render(<ProjectEvidencePage />)
    expect(screen.getByText('Threads')).toBeInTheDocument()
    expect(screen.getByText('Recommended Questions')).toBeInTheDocument()
  })

  it('renders /projects/[id]/compare', () => {
    setProjectRoute(`/projects/${zycProjects[0].project.id}/compare`)
    render(<ProjectComparePage />)
    expect(screen.getByText('Run Compare')).toBeInTheDocument()
    expect(screen.getByText('Latest Compare Summary')).toBeInTheDocument()
  })

  it('renders /projects/[id]/memory', () => {
    setProjectRoute(`/projects/${zycProjects[0].project.id}/memory`)
    render(<ProjectMemoryPage />)
    expect(screen.getByText('Inbox')).toBeInTheDocument()
    expect(screen.getAllByText('Decayed').length).toBeGreaterThan(0)
  })

  it('renders /projects/[id]/outputs', () => {
    setProjectRoute(`/projects/${zycProjects[0].project.id}/outputs`)
    render(<ProjectOutputsPage />)
    expect(screen.getByText('Template Selector')).toBeInTheDocument()
    expect(screen.getByText('Generate')).toBeInTheDocument()
  })

  it('renders /projects/[id]/runs', () => {
    setProjectRoute(`/projects/${zycProjects[0].project.id}/runs`)
    render(<ProjectRunsPage />)
    expect(screen.getByText('Run Goal')).toBeInTheDocument()
  })

  it('renders /projects/[id]/showcase', () => {
    setProjectRoute(`/projects/${zycProjects[0].project.id}/showcase`)
    render(<ProjectShowcasePage />)
    expect(
      screen.getByText('Understand the project, the open risks, and the next moves in one screen.')
    ).toBeInTheDocument()
    expect(
      screen.getByText('Replay the run goal, steps, tools, exceptions, and screenshots.')
    ).toBeInTheDocument()
  })
})
