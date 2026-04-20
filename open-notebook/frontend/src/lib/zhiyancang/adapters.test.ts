import { describe, expect, it } from 'vitest'

import {
  categorizeSource,
  mapLibraryModel,
  mapMemoryItems,
  mapOutputItems,
  mapProjectSummaryToZycProjectCard,
} from './adapters'

describe('zhiyancang adapters', () => {
  it(
    'maps project summary phase and latest fields into project card',
    () => {
      const card = mapProjectSummaryToZycProjectCard({
        id: 'project:demo',
        name: 'Demo',
      description: 'Demo project',
      status: 'active',
      created_at: '2026-04-20T10:00:00Z',
      updated_at: '2026-04-20T10:05:00Z',
      source_count: 3,
      artifact_count: 1,
      memory_count: 2,
      phase: 'compare',
      latest_output_title: 'Competition Brief',
      latest_run_status: 'running',
    })

      expect(card.phase).toBe('compare')
      expect(card.latestOutput).toBe('Competition Brief')
      expect(card.runStatus).toBe('running')
    },
    10000
  )

  it('categorizes sources and aggregates library counts', () => {
    expect(
      categorizeSource({
        id: 'source:image',
        title: 'Image',
        asset: { file_path: '/tmp/demo.png' },
        embedded: false,
        embedded_chunks: 0,
        insights_count: 0,
        created: '2026-04-20T10:00:00Z',
        updated: '2026-04-20T10:00:00Z',
      })
    ).toBe('images')

    const library = mapLibraryModel([
      {
        id: 'source:doc',
        title: 'Doc',
        asset: { file_path: '/tmp/demo.pdf' },
        embedded: true,
        embedded_chunks: 20,
        insights_count: 1,
        created: '2026-04-20T10:00:00Z',
        updated: '2026-04-20T10:00:00Z',
      },
      {
        id: 'source:web',
        title: 'Web',
        asset: { url: 'https://example.com/demo' },
        embedded: true,
        embedded_chunks: 20,
        insights_count: 1,
        created: '2026-04-20T10:00:00Z',
        updated: '2026-04-20T10:00:00Z',
      },
      {
        id: 'source:visual',
        title: 'Visual PDF',
        asset: { file_path: '/tmp/visual.pdf' },
        embedded: true,
        embedded_chunks: 20,
        insights_count: 1,
        visual_index_status: 'completed',
        visual_asset_count: 4,
        created: '2026-04-20T10:00:00Z',
        updated: '2026-04-20T10:00:00Z',
      },
    ])

    expect(library.categories.find((item) => item.id === 'docs')?.count).toBe(1)
    expect(library.categories.find((item) => item.id === 'web')?.count).toBe(1)
    expect(library.categories.find((item) => item.id === 'visual')?.count).toBe(1)
  })

  it('maps memory buckets and output template versions', () => {
    const memory = mapMemoryItems([
      {
        id: 'memory:1',
        scope: 'project',
        type: 'fact',
        text: 'Draft memory',
        confidence: 0.8,
        source_refs: [],
        status: 'draft',
        decay_policy: 'normal',
      },
      {
        id: 'memory:2',
        scope: 'project',
        type: 'risk',
        text: 'Old risk',
        confidence: 0.4,
        source_refs: [],
        status: 'deprecated',
        decay_policy: 'weak',
      },
    ])

    expect(memory[0].bucket).toBe('inbox')
    expect(memory[1].bucket).toBe('decayed')
    expect(memory[1].decay[4]).toBeLessThan(memory[1].decay[0])

    const outputs = mapOutputItems([
      {
        id: 'artifact:latest',
        project_id: 'project:demo',
        artifact_type: 'project_summary',
        title: 'Poster Copy',
        content_md: '# Poster',
        source_refs: [],
        created_by_run_id: 'run:1',
        created_at: '2026-04-20T10:00:00Z',
        updated_at: '2026-04-20T10:05:00Z',
        status: 'ready',
        origin_kind: 'overview',
        origin_id: null,
        thread_id: null,
      },
      {
        id: 'artifact:older',
        project_id: 'project:demo',
        artifact_type: 'project_summary',
        title: 'Poster Copy',
        content_md: '# Older Poster',
        source_refs: [],
        created_by_run_id: 'run:0',
        created_at: '2026-04-20T09:00:00Z',
        updated_at: '2026-04-20T09:05:00Z',
        status: 'draft',
        origin_kind: 'overview',
        origin_id: null,
        thread_id: null,
      },
    ])

    expect(outputs[0].versions).toHaveLength(2)
    expect(outputs[0].template).toBe('Poster Copy')
  })
})
