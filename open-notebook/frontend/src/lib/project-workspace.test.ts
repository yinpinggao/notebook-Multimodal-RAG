import { describe, expect, it } from 'vitest'

import { buildProjectOverviewViewModel, toProjectWorkspaceSummary } from './project-workspace'

describe('project workspace view models', () => {
  it('maps notebook data into a project workspace summary', () => {
    expect(
      toProjectWorkspaceSummary({
        id: 'notebook:alpha',
        name: 'Demo Workspace',
        description: 'Alias-backed project',
        archived: false,
        created: '2026-04-18T08:00:00Z',
        updated: '2026-04-18T09:00:00Z',
        source_count: 4,
        note_count: 2,
      })
    ).toMatchObject({
      id: 'notebook:alpha',
      notebookId: 'notebook:alpha',
      name: 'Demo Workspace',
      status: 'active',
      sourceCount: 4,
      noteCount: 2,
      artifactCount: 0,
      memoryCount: 0,
    })
  })

  it('builds a stable overview model from notebook and source placeholders', () => {
    const overview = buildProjectOverviewViewModel({
      notebook: {
        id: 'notebook:alpha',
        name: '智研舱 Demo',
        description: '竞赛资料整理项目',
        archived: false,
        created: '2026-04-18T08:00:00Z',
        updated: '2026-04-18T09:30:00Z',
        source_count: 2,
        note_count: 1,
      },
      sources: [
        {
          id: 'source:1',
          title: '比赛规则.pdf',
          topics: ['答辩要求', '评分标准'],
          asset: null,
          embedded: true,
          embedded_chunks: 8,
          insights_count: 2,
          created: '2026-04-18T08:20:00Z',
          updated: '2026-04-18T09:20:00Z',
          visual_index_status: 'completed',
        },
        {
          id: 'source:2',
          title: '技术方案.pptx',
          topics: ['方案设计', '评分标准'],
          asset: null,
          embedded: false,
          embedded_chunks: 0,
          insights_count: 1,
          created: '2026-04-18T08:40:00Z',
          updated: '2026-04-18T09:10:00Z',
          status: 'running',
          visual_index_status: 'queued',
        },
      ],
    })

    expect(overview.project.name).toBe('智研舱 Demo')
    expect(overview.topics).toEqual(['答辩要求', '评分标准', '方案设计'])
    expect(overview.stats.embeddedSourceCount).toBe(1)
    expect(overview.stats.visualReadyCount).toBe(1)
    expect(overview.stats.insightCount).toBe(3)
    expect(overview.risks.some((risk) => risk.includes('仍在处理中'))).toBe(true)
    expect(overview.recommendedQuestions.length).toBeGreaterThan(0)
    expect(overview.timelineEvents.length).toBeGreaterThan(0)
  })

  it('falls back to default overview content when a project has no sources yet', () => {
    const overview = buildProjectOverviewViewModel({
      notebook: {
        id: 'notebook:empty',
        name: '空项目',
        description: '',
        archived: false,
        created: '2026-04-18T08:00:00Z',
        updated: '2026-04-18T08:30:00Z',
        source_count: 0,
        note_count: 0,
      },
      sources: [],
    })

    expect(overview.topics).toEqual(['研究目标', '资料结构', '证据线索'])
    expect(overview.risks.some((risk) => risk.includes('尚未导入资料'))).toBe(true)
    expect(overview.recommendedQuestions.length).toBe(3)
  })
})
