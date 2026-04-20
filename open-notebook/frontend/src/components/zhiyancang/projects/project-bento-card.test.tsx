import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { zycProjects } from '@/lib/zhiyancang/mock-data'

import { ProjectBentoCard } from './project-bento-card'

describe('ProjectBentoCard', () => {
  it('renders project phase and headline stats', () => {
    render(<ProjectBentoCard project={zycProjects[0].project} />)

    expect(screen.getByText('Autonomous Defender')).toBeInTheDocument()
    expect(screen.getByText('Compare')).toBeInTheDocument()
    expect(screen.getByText(String(zycProjects[0].project.evidenceCount))).toBeInTheDocument()
    expect(screen.getByText('Defense Pitch v4')).toBeInTheDocument()
  })
})
