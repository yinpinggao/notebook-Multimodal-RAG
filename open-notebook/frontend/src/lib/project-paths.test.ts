import { describe, expect, it } from 'vitest'

import {
  buildContinueProjectPath,
  buildProjectPath,
  isProjectRoute,
} from './project-paths'

describe('project paths', () => {
  it('builds encoded project routes for sections and threads', () => {
    expect(buildProjectPath({ projectId: 'project:demo' })).toBe(
      '/projects/project%3Ademo/overview'
    )
    expect(
      buildProjectPath({
        projectId: 'project:demo',
        section: 'evidence',
        threadId: 'chat_session:alpha',
      })
    ).toBe('/projects/project%3Ademo/evidence/chat_session%3Aalpha')
  })

  it('treats projects index and nested routes as project routes', () => {
    expect(isProjectRoute('/projects')).toBe(true)
    expect(isProjectRoute('/projects/project%3Ademo/overview')).toBe(true)
    expect(isProjectRoute('/assistant')).toBe(false)
  })

  it('falls back to the latest valid thread when the pinned thread is stale', () => {
    expect(
      buildContinueProjectPath({
        projectId: 'project:demo',
        lastProjectId: 'project:demo',
        lastEvidenceThreadId: 'chat_session:missing',
        threads: [
          { id: 'chat_session:older', updated_at: '2026-04-18T09:00:00Z' },
          { id: 'chat_session:latest', updated_at: '2026-04-19T09:00:00Z' },
        ],
      })
    ).toBe('/projects/project%3Ademo/evidence/chat_session%3Alatest')
  })

  it('returns the project overview when there is no available thread', () => {
    expect(
      buildContinueProjectPath({
        projectId: 'project:demo',
        lastProjectId: 'project:demo',
        lastEvidenceThreadId: 'chat_session:missing',
        threads: [],
      })
    ).toBe('/projects/project%3Ademo/overview')
  })
})
