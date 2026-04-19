import { redirect } from 'next/navigation'
import { describe, expect, it, vi } from 'vitest'

vi.mock('next/navigation', () => ({
  redirect: vi.fn(),
}))

import DashboardHomePage from './page'

describe('DashboardHomePage', () => {
  it('redirects the legacy dashboard route to projects', () => {
    DashboardHomePage()

    expect(redirect).toHaveBeenCalledWith('/projects')
  })
})
