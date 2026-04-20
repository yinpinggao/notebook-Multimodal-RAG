import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProjectOutputsPage from './page'
import { zycProjects } from '@/lib/zhiyancang/mock-data'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import { mockUseParams } from '@/test/setup'

vi.mock('@/lib/hooks/use-zyc-project-detail', () => ({
  useZycProjectDetail: () => ({
    data: zycProjects[1],
    isLoading: false,
    error: null,
    meta: {
      compares: [{ id: 'compare:1' }],
      activeThreadId: 'thread:1',
    },
  }),
}))

vi.mock('@/lib/hooks/use-project-artifacts', () => ({
  useCreateProjectArtifact: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
  useRegenerateProjectArtifact: () => ({ isPending: false, error: null, mutateAsync: vi.fn() }),
  useProjectArtifact: () => ({ data: null, error: null }),
}))

vi.mock('@/lib/hooks/use-media-query', () => ({
  useMediaQuery: (query: string) => query.includes('min-width'),
}))

describe('ProjectOutputsPage', () => {
  beforeEach(() => {
    mockUseParams.mockReturnValue({ projectId: zycProjects[1].project.id })
    useZycUIStore.setState({
      activeGlobalSection: 'projects',
      activeProjectSection: 'outputs',
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
      workspaceRetrievalMode: 'hybrid',
      workspaceMemoryScope: 'Project Memory',
    })
  })

  it('keeps the selected generation template and syncs the active version to the current project', async () => {
    render(<ProjectOutputsPage />)

    expect(screen.getByText('Template Selector')).toBeInTheDocument()

    await waitFor(() => {
      const state = useZycUIStore.getState()
      expect(state.selectedOutputTemplate).toBe('Defense Pitch')
      expect(state.selectedOutputVersionId).toBe('cov1')
    })
  })
})
