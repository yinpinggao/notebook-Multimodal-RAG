import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

const useAssistantWorkspaceStoreMock = vi.hoisted(() =>
  vi.fn(() => ({
    currentProjectId: 'project:demo',
    currentView: 'workspace',
    knowledgeCollapsed: false,
    memoryCollapsed: false,
    setKnowledgeCollapsed: vi.fn(),
    setMemoryCollapsed: vi.fn(),
  }))
)

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/assistant',
  useSearchParams: () => new URLSearchParams('project=project%3Ademo&view=workspace'),
}))

vi.mock('@/lib/hooks/use-create-dialogs', () => ({
  useCreateDialogs: vi.fn(() => ({
    openNotebookDialog: vi.fn(),
  })),
}))

vi.mock('@/lib/hooks/use-media-query', () => ({
  useIsDesktop: vi.fn(() => true),
}))

vi.mock('@/lib/hooks/use-projects', () => ({
  useProjects: vi.fn(() => ({
    data: [{ id: 'project:demo', name: 'Demo Project', updated_at: '2026-04-19T00:00:00Z' }],
    isLoading: false,
  })),
}))

vi.mock('@/lib/stores/assistant-workspace-store', () => ({
  useAssistantWorkspaceStore: useAssistantWorkspaceStoreMock,
}))

vi.mock('@/components/harness/KnowledgePanel', () => ({
  KnowledgePanel: () => <div>Knowledge panel</div>,
}))

vi.mock('@/components/harness/AgentPanel', () => ({
  AgentPanel: () => <div>Agent panel</div>,
}))

vi.mock('@/components/harness/MemoryPanel', () => ({
  MemoryPanel: () => <div>Memory panel</div>,
}))

vi.mock('@/components/harness/AssistantViewPanels', () => ({
  KnowledgePreviewPanel: () => <div>Knowledge preview</div>,
  MemoryDetailPanel: () => <div>Memory detail</div>,
  MemorySourceRefsRail: () => <div>Memory refs</div>,
  PinnedContextRail: () => <div>Pinned context</div>,
  WorkspaceSupportRail: () => <div>Workspace support</div>,
}))

import AssistantPage from './page'

describe('AssistantPage', () => {
  it('renders the knowledge layout without the full chat panel', () => {
    useAssistantWorkspaceStoreMock.mockReturnValue({
      currentProjectId: 'project:demo',
      currentView: 'knowledge',
      knowledgeCollapsed: false,
      memoryCollapsed: false,
      setKnowledgeCollapsed: vi.fn(),
      setMemoryCollapsed: vi.fn(),
    })

    render(<AssistantPage />)

    expect(screen.getByText('Knowledge panel')).toBeInTheDocument()
    expect(screen.getByText('Knowledge preview')).toBeInTheDocument()
    expect(screen.queryByText('Agent panel')).toBeNull()
  })

  it('renders the workspace layout with the full chat panel', () => {
    useAssistantWorkspaceStoreMock.mockReturnValue({
      currentProjectId: 'project:demo',
      currentView: 'workspace',
      knowledgeCollapsed: false,
      memoryCollapsed: false,
      setKnowledgeCollapsed: vi.fn(),
      setMemoryCollapsed: vi.fn(),
    })

    render(<AssistantPage />)

    expect(screen.getByText('Knowledge panel')).toBeInTheDocument()
    expect(screen.getByText('Agent panel')).toBeInTheDocument()
    expect(screen.getByText('Workspace support')).toBeInTheDocument()
  })

  it('renders the memory layout without the full chat panel', () => {
    useAssistantWorkspaceStoreMock.mockReturnValue({
      currentProjectId: 'project:demo',
      currentView: 'memory',
      knowledgeCollapsed: false,
      memoryCollapsed: false,
      setKnowledgeCollapsed: vi.fn(),
      setMemoryCollapsed: vi.fn(),
    })

    render(<AssistantPage />)

    expect(screen.getByText('Memory panel')).toBeInTheDocument()
    expect(screen.getByText('Memory detail')).toBeInTheDocument()
    expect(screen.queryByText('Agent panel')).toBeNull()
  })
})
