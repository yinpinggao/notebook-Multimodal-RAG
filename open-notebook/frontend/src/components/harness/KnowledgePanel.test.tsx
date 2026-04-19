import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { KnowledgePanel } from './KnowledgePanel'

const { openModalMock } = vi.hoisted(() => ({
  openModalMock: vi.fn(),
}))

vi.mock('@/lib/hooks/use-projects', () => ({
  useProjects: vi.fn(() => ({
    data: [{ id: 'project:demo', name: 'Demo Project' }],
  })),
}))

vi.mock('@/lib/hooks/use-sources', () => ({
  useNotebookSources: vi.fn(() => ({
    sources: [
      {
        id: 'source:1',
        title: 'Competition Spec',
        embedded: true,
        embedded_chunks: 3,
        insights_count: 2,
        created: '2026-04-18T00:00:00Z',
        updated: '2026-04-18T00:00:00Z',
        asset: null,
      },
    ],
    isLoading: false,
  })),
}))

vi.mock('@/lib/hooks/use-notes', () => ({
  useNotes: vi.fn(() => ({
    data: [
      {
        id: 'note:1',
        title: 'Review notes',
        content: 'Need to explain the system pipeline',
      },
    ],
    isLoading: false,
  })),
}))

vi.mock('@/lib/hooks/use-modal-manager', () => ({
  useModalManager: vi.fn(() => ({
    openModal: openModalMock,
  })),
}))

vi.mock('@/lib/stores/assistant-workspace-store', () => ({
  useAssistantWorkspaceStore: vi.fn(() => ({
    selectedContextItems: [],
    toggleContextItem: vi.fn(),
    toggleKnowledgeCollapsed: vi.fn(),
  })),
}))

vi.mock('@/components/sources/AddSourceDialog', () => ({
  AddSourceDialog: () => null,
}))

vi.mock('@/app/(dashboard)/notebooks/components/NoteEditorDialog', () => ({
  NoteEditorDialog: () => null,
}))

describe('KnowledgePanel', () => {
  it('renders grouped items and filters them by search', () => {
    render(<KnowledgePanel projectId="project:demo" />)

    expect(screen.getByText('Competition Spec')).toBeInTheDocument()
    expect(screen.getByText('Review notes')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('Search...'), {
      target: { value: 'pipeline' },
    })

    expect(screen.queryByText('Competition Spec')).toBeNull()
    expect(screen.getByText('Review notes')).toBeInTheDocument()
  })

  it('uses preview selection instead of opening the modal when a preview handler is provided', () => {
    const onPreviewSelect = vi.fn()

    render(
      <KnowledgePanel
        projectId="project:demo"
        onPreviewSelect={onPreviewSelect}
      />
    )

    fireEvent.click(screen.getByText('Competition Spec'))

    expect(onPreviewSelect).toHaveBeenCalledWith({
      id: 'source:1',
      type: 'source',
    })
    expect(openModalMock).not.toHaveBeenCalled()
  })
})
