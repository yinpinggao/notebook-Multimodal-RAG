import { redirect } from 'next/navigation'
import { describe, expect, it, vi } from 'vitest'

vi.mock('next/navigation', () => ({
  redirect: vi.fn(),
}))

import ProjectIndexPage from './page'

describe('ProjectIndexPage', () => {
  it('redirects to the overview route without crashing on literal percent signs', async () => {
    await ProjectIndexPage({
      params: Promise.resolve({ projectId: 'project 100%' }),
    })

    expect(redirect).toHaveBeenCalledWith('/projects/project%20100%25/overview')
  })
})
