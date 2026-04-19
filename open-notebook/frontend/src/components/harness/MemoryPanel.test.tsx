import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { MemoryPanel } from './MemoryPanel'

const toggleContextItem = vi.fn()

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>()
  return {
    ...actual,
    useQueryClient: vi.fn(() => ({
      invalidateQueries: vi.fn(),
    })),
  }
})

vi.mock('@/lib/hooks/use-project-memory', () => ({
  useProjectMemory: vi.fn(() => ({
    data: [
      {
        id: 'memory:1',
        scope: 'project',
        type: 'fact',
        text: 'The judges care about evidence.',
        confidence: 0.8,
        source_refs: [],
        status: 'accepted',
        decay_policy: 'weak',
      },
      {
        id: 'memory:2',
        scope: 'project',
        type: 'risk',
        text: 'Missing screenshots will hurt the demo.',
        confidence: 0.7,
        source_refs: [],
        status: 'draft',
        decay_policy: 'normal',
      },
    ],
    isLoading: false,
  })),
  useCreateProjectMemory: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useRebuildProjectMemory: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}))

vi.mock('@/lib/stores/assistant-workspace-store', () => ({
  useAssistantWorkspaceStore: vi.fn(() => ({
    selectedContextItems: [],
    toggleContextItem,
    toggleMemoryCollapsed: vi.fn(),
  })),
}))

describe('MemoryPanel', () => {
  it('filters memory items and adds one to context', () => {
    render(<MemoryPanel projectId="project:demo" />)

    fireEvent.change(screen.getByPlaceholderText('Search memory'), {
      target: { value: 'screenshots' },
    })

    expect(screen.queryByText('The judges care about evidence.')).toBeNull()
    expect(screen.getByText('Missing screenshots will hurt the demo.')).toBeInTheDocument()

    fireEvent.click(screen.getAllByText('Add')[0])

    expect(toggleContextItem).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'memory:2',
        type: 'memory',
      })
    )
  })

  it('notifies the selected memory when a list item is clicked', () => {
    const onSelectMemory = vi.fn()

    render(
      <MemoryPanel
        projectId="project:demo"
        onSelectMemory={onSelectMemory}
      />
    )

    fireEvent.click(screen.getByText('The judges care about evidence.'))

    expect(onSelectMemory).toHaveBeenCalledWith('memory:1')
  })
})
