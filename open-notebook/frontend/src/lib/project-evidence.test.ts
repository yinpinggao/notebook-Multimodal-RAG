import { describe, expect, it } from 'vitest'

import {
  buildProjectEvidencePath,
  canContinueEvidenceThread,
  evidenceThreadIdFromRoute,
  formatEvidenceConfidence,
  resolveEvidenceTarget,
} from './project-evidence'

describe('project evidence helpers', () => {
  it('builds encoded evidence routes for project threads', () => {
    expect(buildProjectEvidencePath('project:demo')).toBe('/projects/project%3Ademo/evidence')
    expect(buildProjectEvidencePath('project:demo', 'chat_session:alpha')).toBe(
      '/projects/project%3Ademo/evidence/chat_session%3Aalpha'
    )
  })

  it('decodes thread ids from route params without throwing on malformed input', () => {
    expect(evidenceThreadIdFromRoute('chat_session%3Aalpha')).toBe('chat_session:alpha')
    expect(evidenceThreadIdFromRoute('chat_session%zzalpha')).toBe('chat_session%zzalpha')
  })

  it('resolves source, note, and insight targets from evidence references', () => {
    expect(
      resolveEvidenceTarget({
        sourceId: 'source:alpha',
        internalRef: 'source:alpha#p5',
      })
    ).toEqual({
      kind: 'source',
      id: 'source:alpha',
    })

    expect(
      resolveEvidenceTarget({
        sourceId: 'note:brief',
        internalRef: 'note:brief',
      })
    ).toEqual({
      kind: 'note',
      id: 'note:brief',
    })

    expect(
      resolveEvidenceTarget({
        internalRef: 'source_insight:vision#chunk-1',
      })
    ).toEqual({
      kind: 'insight',
      id: 'source_insight:vision',
    })
  })

  it('formats confidence values into stable percentage labels', () => {
    expect(formatEvidenceConfidence(0.84)).toBe('84%')
    expect(formatEvidenceConfidence(1.5)).toBe('100%')
    expect(formatEvidenceConfidence(null)).toBe('待评估')
  })

  it('only allows followup when the target thread is loaded and valid', () => {
    expect(
      canContinueEvidenceThread({
        threadId: 'chat_session:demo',
        threadLoaded: true,
        threadError: false,
      })
    ).toBe(true)

    expect(
      canContinueEvidenceThread({
        threadId: 'chat_session:demo',
        threadLoaded: false,
        threadError: false,
      })
    ).toBe(false)

    expect(
      canContinueEvidenceThread({
        threadId: 'chat_session:demo',
        threadLoaded: true,
        threadError: true,
      })
    ).toBe(false)
  })
})
