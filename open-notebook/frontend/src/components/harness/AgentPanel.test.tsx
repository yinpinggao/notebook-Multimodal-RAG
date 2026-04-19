import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AgentPanel } from './AgentPanel'

const {
  askMutateAsync,
  followupMutateAsync,
  useProjectThreadMock,
  useAssistantWorkspaceStoreMock,
} = vi.hoisted(() => ({
  askMutateAsync: vi.fn().mockResolvedValue({
    thread_id: 'chat_session:new',
    answer: 'Use the visual evidence.',
    confidence: 0.8,
    evidence_cards: [],
    memory_updates: [],
    run_id: 'run:1',
    suggested_followups: [],
    mode: 'visual',
  }),
  followupMutateAsync: vi.fn(),
  useProjectThreadMock: vi.fn(() => ({
    data: undefined,
    isLoading: false,
    isFetching: false,
    error: null,
  })),
  useAssistantWorkspaceStoreMock: vi.fn(() => ({
    currentAgent: 'visual',
    currentThreadId: undefined as string | undefined,
    selectedContextItems: [
      { id: 'source:1', type: 'source', label: 'Spec' },
      { id: 'memory:1', type: 'memory', label: 'Preference' },
    ],
    toggleContextItem: vi.fn(),
    removeContextItem: vi.fn(),
    clearContextItems: vi.fn(),
  })),
}))

vi.mock('@/lib/hooks/use-project-evidence', () => ({
  useProjectThreads: vi.fn(() => ({ data: [] })),
  useProjectThread: useProjectThreadMock,
  useAskProject: vi.fn(() => ({
    mutateAsync: askMutateAsync,
    isPending: false,
  })),
  useFollowupProjectThread: vi.fn(() => ({
    mutateAsync: followupMutateAsync,
    isPending: false,
  })),
}))

vi.mock('@/lib/hooks/use-project-memory', () => ({
  useProjectMemory: vi.fn(() => ({ data: [], isLoading: false })),
  useCreateProjectMemory: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
}))

vi.mock('@/lib/hooks/use-notes', () => ({
  useNotes: vi.fn(() => ({ data: [], isLoading: false })),
}))

vi.mock('@/lib/hooks/use-sources', () => ({
  useNotebookSources: vi.fn(() => ({
    sources: [],
    isLoading: false,
  })),
}))

vi.mock('@/lib/stores/assistant-workspace-store', () => ({
  useAssistantWorkspaceStore: useAssistantWorkspaceStoreMock,
}))

describe('AgentPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('submits only the selected context ids with the mapped ask mode', async () => {
    useProjectThreadMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
      error: null,
    })
    useAssistantWorkspaceStoreMock.mockReturnValue({
      currentAgent: 'visual',
      currentThreadId: undefined,
      selectedContextItems: [
        { id: 'source:1', type: 'source', label: 'Spec' },
        { id: 'memory:1', type: 'memory', label: 'Preference' },
      ],
      toggleContextItem: vi.fn(),
      removeContextItem: vi.fn(),
      clearContextItems: vi.fn(),
    })

    render(<AgentPanel projectId="project:demo" />)

    fireEvent.change(
      screen.getByPlaceholderText(
        'Ask a concrete question, or drop pinned context here before sending.'
      ),
      {
        target: { value: 'What should we show first?' },
      }
    )

    fireEvent.click(screen.getByText('Send'))

    await waitFor(() => {
      expect(askMutateAsync).toHaveBeenCalledWith({
        question: 'What should we show first?',
        mode: 'visual',
        agent: 'visual',
        source_ids: ['source:1'],
        note_ids: [],
        memory_ids: ['memory:1'],
      })
    })
  })

  it('does not submit a follow-up until the selected thread has loaded', async () => {
    useProjectThreadMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetching: false,
      error: null,
    })
    useAssistantWorkspaceStoreMock.mockReturnValue({
      currentAgent: 'visual',
      currentThreadId: 'chat_session:loading',
      selectedContextItems: [],
      toggleContextItem: vi.fn(),
      removeContextItem: vi.fn(),
      clearContextItems: vi.fn(),
    })

    render(<AgentPanel projectId="project:demo" />)

    fireEvent.change(
      screen.getByPlaceholderText(
        'Ask a concrete question, or drop pinned context here before sending.'
      ),
      {
        target: { value: 'Should stay on this thread?' },
      }
    )

    fireEvent.click(screen.getByText('Send'))

    await waitFor(() => {
      expect(askMutateAsync).not.toHaveBeenCalled()
      expect(followupMutateAsync).not.toHaveBeenCalled()
    })
  })

  it('keeps the message stream in a shrinkable scroll container', () => {
    render(<AgentPanel projectId="project:demo" />)

    expect(screen.getByTestId('agent-message-scroll')).toHaveClass(
      'min-h-0',
      'flex-1',
      'overflow-hidden'
    )
  })

  it('does not render the latest ai answer twice when thread history already includes it', () => {
    useProjectThreadMock.mockReturnValue({
      data: {
        id: 'chat_session:demo',
        project_id: 'project:demo',
        title: 'Thread',
        created_at: '2026-04-19T00:00:00Z',
        updated_at: '2026-04-19T00:00:00Z',
        message_count: 2,
        messages: [
          {
            id: 'msg:user',
            type: 'human',
            content: '你能看见什么？',
          },
          {
            id: 'msg:ai',
            type: 'ai',
            content: 'Repeated answer',
          },
        ],
        latest_response: {
          answer: 'Repeated answer',
          confidence: 0.8,
          evidence_cards: [],
          memory_updates: [],
          run_id: 'run:1',
          suggested_followups: [],
          mode: 'visual',
        },
      },
      isLoading: false,
      isFetching: false,
      error: null,
    } as any)
    useAssistantWorkspaceStoreMock.mockReturnValue({
      currentAgent: 'visual',
      currentThreadId: 'chat_session:demo',
      selectedContextItems: [],
      toggleContextItem: vi.fn(),
      removeContextItem: vi.fn(),
      clearContextItems: vi.fn(),
    })

    render(<AgentPanel projectId="project:demo" />)

    expect(screen.getAllByText('Repeated answer')).toHaveLength(1)
  })
})
