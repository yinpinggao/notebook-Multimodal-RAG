'use client'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { ProjectBentoCard } from '@/components/zhiyancang/projects/project-bento-card'
import { ProjectsHero } from '@/components/zhiyancang/projects/projects-hero'
import { useZycProjects } from '@/lib/hooks/use-zyc-projects'
import { formatApiError } from '@/lib/utils/error-handler'

export default function ProjectsPage() {
  const { data, error, isLoading } = useZycProjects()

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Projects unavailable</AlertTitle>
        <AlertDescription>{formatApiError(error)}</AlertDescription>
      </Alert>
    )
  }

  if (isLoading || !data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <ProjectsHero latestProjectId={data.latestProjectId} />

      <section className="space-y-4">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-white/40">
              Global Layer / Projects
            </div>
            <h2 className="mt-2 text-2xl font-semibold text-white">Active Research Tracks</h2>
          </div>
          <p className="max-w-2xl text-sm leading-7 text-white/58">
            Every card is phase-aware and keeps evidence, memory, outputs, and run state visible
            in one clean grid.
          </p>
        </div>

        {data.projects.length === 0 ? (
          <div className="rounded-[24px] border border-dashed border-white/12 px-6 py-10 text-sm text-white/55">
            No projects yet. Create one, then start importing sources and asking evidence-grounded
            questions.
          </div>
        ) : (
          <div className="grid gap-5 xl:grid-cols-3">
            {data.projects.map((project) => (
              <ProjectBentoCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
