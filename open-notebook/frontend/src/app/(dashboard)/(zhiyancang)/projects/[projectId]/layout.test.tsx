import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/components/zhiyancang/layout/project-subnav', () => ({
  ProjectSubnav: ({ projectId }: { projectId: string }) => (
    <div data-testid="project-subnav">{projectId}</div>
  ),
}))

import ProjectLayout from './layout'

describe('ProjectLayout', () => {
  it('renders the project subnav without server-side project validation', async () => {
    const result = await ProjectLayout({
      children: <div>child content</div>,
      params: Promise.resolve({ projectId: 'project:live' }),
    })

    render(result)

    expect(screen.getByTestId('project-subnav')).toHaveTextContent('project:live')
    expect(screen.getByText('child content')).toBeInTheDocument()
  })
})
