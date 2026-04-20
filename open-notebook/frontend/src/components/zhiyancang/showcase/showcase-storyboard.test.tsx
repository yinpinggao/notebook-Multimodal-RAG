import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { zycProjects } from '@/lib/zhiyancang/mock-data'

import { ShowcaseStoryboard } from './showcase-storyboard'

describe('ShowcaseStoryboard', () => {
  it('renders storyboard sections in order', () => {
    render(<ShowcaseStoryboard record={zycProjects[0]} />)

    expect(screen.getAllByText('Overview').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Evidence').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Compare').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Memory').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Outputs').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Runs').length).toBeGreaterThan(0)
  })
})
