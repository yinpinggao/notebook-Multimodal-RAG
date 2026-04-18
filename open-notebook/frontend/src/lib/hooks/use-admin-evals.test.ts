import { describe, expect, it } from 'vitest'

import { readProjectEvalOutput, readProjectIdFromEvalJob } from './use-admin-evals'

describe('use-admin-evals helpers', () => {
  it('reads eval output from command result payload', () => {
    const output = readProjectEvalOutput({
      result: {
        project_id: 'project:demo',
        summary: '当前项目通过了 2/3 项最小评测。',
        metrics: [],
        passed_metrics: 2,
        available_metrics: 3,
      },
    })

    expect(output?.project_id).toBe('project:demo')
    expect(output?.summary).toBe('当前项目通过了 2/3 项最小评测。')
  })

  it('falls back to args.project_id when job result is not ready yet', () => {
    const projectId = readProjectIdFromEvalJob({
      args: {
        project_id: 'project:demo',
      },
      result: null,
    })

    expect(projectId).toBe('project:demo')
  })
})
