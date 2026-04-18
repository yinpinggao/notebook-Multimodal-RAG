import { describe, expect, it } from 'vitest'

import {
  notebookIdToProjectId,
  notebookToProjectSummary,
  projectIdToNotebookId,
} from './project-alias'

describe('project alias helpers', () => {
  it('maps an encoded project route id back to notebook id once', () => {
    expect(projectIdToNotebookId('notebook%3Aalpha')).toBe('notebook:alpha')
    expect(projectIdToNotebookId('notebook:alpha')).toBe('notebook:alpha')
  })

  it('leaves malformed route ids untouched instead of throwing', () => {
    expect(projectIdToNotebookId('notebook%zzalpha')).toBe('notebook%zzalpha')
  })

  it('converts notebook responses into project summaries', () => {
    expect(
      notebookToProjectSummary({
        id: 'notebook:demo',
        name: 'Demo Project',
        description: 'Alias-backed project',
        archived: false,
        created: '2026-04-18T00:00:00Z',
        updated: '2026-04-18T01:00:00Z',
        source_count: 3,
        note_count: 2,
      })
    ).toEqual({
      id: notebookIdToProjectId('notebook:demo'),
      notebookId: 'notebook:demo',
      name: 'Demo Project',
      description: 'Alias-backed project',
      archived: false,
      created: '2026-04-18T00:00:00Z',
      updated: '2026-04-18T01:00:00Z',
      sourceCount: 3,
      noteCount: 2,
    })
  })
})
