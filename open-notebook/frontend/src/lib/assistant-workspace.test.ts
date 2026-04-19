import { describe, expect, it } from 'vitest'

import {
  buildAssistantUrl,
  groupAssistantContextItems,
  resolveAssistantProjectId,
} from '@/lib/assistant-workspace'

describe('assistant workspace helpers', () => {
  it('builds assistant urls with shared query state', () => {
    expect(
      buildAssistantUrl({
        projectId: 'project:demo',
        view: 'memory',
        agent: 'visual',
        threadId: 'chat_session:1',
      })
    ).toBe(
      '/assistant?project=project%3Ademo&view=memory&agent=visual&thread=chat_session%3A1'
    )
  })

  it('resolves the requested project first, then last project, then most recent', () => {
    const projects = [
      {
        id: 'project:older',
        name: 'Older',
        description: '',
        status: 'active' as const,
        created_at: '2026-04-17T00:00:00Z',
        updated_at: '2026-04-17T00:00:00Z',
        source_count: 0,
        artifact_count: 0,
        memory_count: 0,
      },
      {
        id: 'project:newer',
        name: 'Newer',
        description: '',
        status: 'active' as const,
        created_at: '2026-04-18T00:00:00Z',
        updated_at: '2026-04-18T00:00:00Z',
        source_count: 0,
        artifact_count: 0,
        memory_count: 0,
      },
    ]

    expect(
      resolveAssistantProjectId({
        projects,
        requestedProjectId: 'project:older',
        lastProjectId: 'project:newer',
      })
    ).toBe('project:older')

    expect(
      resolveAssistantProjectId({
        projects,
        requestedProjectId: 'project:missing',
        lastProjectId: 'project:older',
      })
    ).toBe('project:older')

    expect(
      resolveAssistantProjectId({
        projects,
      })
    ).toBe('project:newer')
  })

  it('groups selected context ids by item type', () => {
    expect(
      groupAssistantContextItems([
        { id: 'source:1', type: 'source', label: 'Spec' },
        { id: 'note:1', type: 'note', label: 'Summary' },
        { id: 'memory:1', type: 'memory', label: 'Preference' },
      ])
    ).toEqual({
      sourceIds: ['source:1'],
      noteIds: ['note:1'],
      memoryIds: ['memory:1'],
    })
  })
})
