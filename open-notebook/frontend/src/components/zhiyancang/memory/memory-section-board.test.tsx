import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { zycProjects } from '@/lib/zhiyancang/mock-data'

import { MemorySectionBoard } from './memory-section-board'

describe('MemorySectionBoard', () => {
  it('renders the four memory buckets and decay curve content', () => {
    render(<MemorySectionBoard items={zycProjects[0].memory} />)

    expect(screen.getByText('Inbox')).toBeInTheDocument()
    expect(screen.getByText('Stable')).toBeInTheDocument()
    expect(screen.getAllByText('Frozen').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Decayed').length).toBeGreaterThan(0)
    expect(document.querySelector('svg')).not.toBeNull()
  })
})
