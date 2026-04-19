import { redirect } from 'next/navigation'
import { describe, expect, it, vi } from 'vitest'

vi.mock('next/navigation', () => ({
  redirect: vi.fn(),
}))

import NotebookPageRedirect from './page'

describe('NotebookPageRedirect', () => {
  it('redirects to the overview route without re-decoding the notebook id', async () => {
    await NotebookPageRedirect({
      params: Promise.resolve({ id: 'demo 100%' }),
    })

    expect(redirect).toHaveBeenCalledWith('/projects/demo%20100%25/overview')
  })
})
