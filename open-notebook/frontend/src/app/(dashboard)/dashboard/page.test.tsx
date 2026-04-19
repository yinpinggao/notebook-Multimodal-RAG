import { ReactNode } from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

vi.mock('@/components/projects/project-card', () => ({
  ProjectCard: ({ href, ctaLabel }: { href: string; ctaLabel?: string }) => (
    <a href={href}>{ctaLabel || 'Project'}</a>
  ),
}))

vi.mock('@/lib/hooks/use-create-dialogs', () => ({
  useCreateDialogs: vi.fn(() => ({
    openNotebookDialog: vi.fn(),
    openSourceDialog: vi.fn(),
  })),
}))

vi.mock('@/lib/hooks/use-models', () => ({
  useModels: vi.fn(() => ({
    data: [],
    isLoading: false,
  })),
  useModelDefaults: vi.fn(() => ({
    data: {},
  })),
}))

vi.mock('@/lib/hooks/use-project-evidence', () => ({
  useProjectThreads: vi.fn(() => ({
    data: [],
  })),
}))

vi.mock('@/lib/hooks/use-projects', () => ({
  useProjects: vi.fn(() => ({
    data: [
      {
        id: 'project:demo',
        name: 'Demo Project',
        description: '',
        status: 'active',
        created_at: '2026-04-19T00:00:00Z',
        updated_at: '2026-04-19T00:00:00Z',
        source_count: 2,
        artifact_count: 0,
        memory_count: 0,
      },
    ],
    isLoading: false,
  })),
}))

vi.mock('@/lib/stores/assistant-workspace-store', () => ({
  useAssistantWorkspaceStore: vi.fn(() => ({
    lastProjectId: 'project:demo',
  })),
}))

import DashboardHomePage from './page'

describe('DashboardHomePage', () => {
  it('shows the models setup card and routes projects into knowledge view by default', () => {
    render(<DashboardHomePage />)

    expect(screen.getByText('Configure Models')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Knowledge Hub' })[0]).toHaveAttribute(
      'href',
      '/assistant?project=project%3Ademo&view=knowledge'
    )
  })
})
