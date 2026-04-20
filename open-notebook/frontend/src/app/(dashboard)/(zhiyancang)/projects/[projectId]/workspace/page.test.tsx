import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProjectWorkspacePage from './page'
import { zycProjects } from '@/lib/zhiyancang/mock-data'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import { mockUseParams } from '@/test/setup'

vi.mock('@/lib/hooks/use-zyc-project-detail', () => ({
  useZycProjectDetail: () => ({
    data: zycProjects[2],
    isLoading: false,
    error: null,
    meta: {
      activeThreadId: 'thread:1',
      activeThread: {
        latest_response: {
          answer: 'Answer',
          evidence_cards: [],
        },
      },
    },
  }),
}))

vi.mock('@/lib/hooks/use-project-memory', () => ({
  useCreateProjectMemory: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
}))

vi.mock('@/lib/hooks/use-project-artifacts', () => ({
  useCreateProjectArtifact: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
}))

vi.mock('@/lib/hooks/use-media-query', () => ({
  useMediaQuery: (query: string) => query.includes('min-width'),
}))

describe('ProjectWorkspacePage', () => {
  beforeEach(() => {
    mockUseParams.mockReturnValue({ projectId: zycProjects[2].project.id })
    useZycUIStore.setState({
      activeGlobalSection: 'projects',
      activeProjectSection: 'workspace',
      mobileNavOpen: false,
      workspaceLeftOpen: false,
      workspaceRightOpen: false,
      evidenceFilterOpen: false,
      outputHistoryOpen: false,
      demoMode: false,
      activeEvidenceType: 'docs',
      activeSearchMode: 'hybrid',
      selectedCompareSourceA: 's1',
      selectedCompareSourceB: 's2',
      selectedOutputTemplate: 'Defense Pitch',
      selectedOutputVersionId: 'v1',
      workspaceRetrievalMode: 'rrf',
      workspaceMemoryScope: 'Frozen Only',
    })
  })

  it('normalizes retrieval and memory selectors to the current project options', async () => {
    render(<ProjectWorkspacePage />)

    expect(screen.getByText('Researcher')).toBeInTheDocument()

    await waitFor(() => {
      const state = useZycUIStore.getState()
      expect(state.workspaceRetrievalMode).toBe('keyword')
      expect(state.workspaceMemoryScope).toBe('Project Memory')
    })
  })
})
