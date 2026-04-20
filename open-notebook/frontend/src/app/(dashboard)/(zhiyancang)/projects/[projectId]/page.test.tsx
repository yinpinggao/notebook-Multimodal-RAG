import { redirect } from 'next/navigation'
import { describe, expect, it, vi } from 'vitest'

vi.mock('next/navigation', () => ({
  redirect: vi.fn(),
}))

import ProjectIndexPage from './page'

describe('ProjectIndexPage', () => {
  it('always redirects project ids to the overview route', async () => {
    await ProjectIndexPage({
      params: Promise.resolve({ projectId: 'project:demo' }),
    })

    expect(redirect).toHaveBeenCalledWith('/projects/project%3Ademo/overview')
  })
})
