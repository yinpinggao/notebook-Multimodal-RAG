'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect } from 'react'
import { faBolt, faPlay } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Button } from '@/components/ui/button'
import { useZycProjectDetail } from '@/lib/hooks/use-zyc-project-detail'
import { useTranslation } from '@/lib/hooks/use-translation'
import { buildProjectPath } from '@/lib/project-paths'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import { type ProjectSection } from '@/lib/zhiyancang/types'
import { cn } from '@/lib/utils'

const PROJECT_TAB_IDS: ProjectSection[] = [
  'overview',
  'workspace',
  'evidence',
  'compare',
  'memory',
  'outputs',
  'runs',
  'showcase',
]

export function ProjectSubnav({ projectId }: { projectId: string }) {
  const pathname = usePathname()
  const { data } = useZycProjectDetail(projectId)
  const { t } = useTranslation()
  const { setActiveProjectSection, setDemoMode } = useZycUIStore()

  const projectTabs: Array<{ id: ProjectSection; label: string; navigationLabel: string }> = [
    { id: 'overview', label: t.navigation.overview, navigationLabel: t.navigation.overview },
    { id: 'workspace', label: t.zhiyancang.workspace, navigationLabel: t.navigation.workspace },
    { id: 'evidence', label: t.navigation.evidence, navigationLabel: t.navigation.evidence },
    { id: 'compare', label: t.navigation.compare, navigationLabel: t.navigation.compare },
    { id: 'memory', label: t.navigation.memory, navigationLabel: t.navigation.memory },
    { id: 'outputs', label: t.navigation.outputs, navigationLabel: t.navigation.outputs },
    { id: 'runs', label: t.navigation.runs, navigationLabel: t.navigation.runs },
    { id: 'showcase', label: t.zhiyancang.showcase, navigationLabel: t.navigation.showcase },
  ]

  useEffect(() => {
    const matchedSection =
      PROJECT_TAB_IDS.find((section) => {
        const href = buildProjectPath({ projectId, section })
        return pathname === href || pathname.startsWith(`${href}/`)
      }) ?? 'overview'
    setActiveProjectSection(matchedSection)
  }, [pathname, projectId, setActiveProjectSection])

  return (
    <div className="zyc-page-enter zyc-glass rounded-[24px] px-4 py-4 lg:px-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs uppercase tracking-[0.16em] text-white/60">
            <FontAwesomeIcon icon={faBolt} className="text-[11px]" />
            Project Layer
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white lg:text-[2rem]">
              {data?.project.name ?? 'Project Workspace'}
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-white/62">
              {data?.project.objective ??
                'A clean operating system for evidence, memory, outputs, and runs.'}
            </p>
          </div>
        </div>

        <Button
          asChild
          className="zyc-touch zyc-ripple rounded-full bg-white text-zinc-950 hover:bg-white/90"
          onClick={() => setDemoMode(true)}
        >
          <Link href={buildProjectPath({ projectId, section: 'showcase' })}>
            <FontAwesomeIcon icon={faPlay} className="mr-2 text-sm" />
            Demo Mode
          </Link>
        </Button>
      </div>

      <div className="mt-5 flex gap-2 overflow-x-auto pb-1">
        {projectTabs.map((tab) => {
          const href = buildProjectPath({ projectId, section: tab.id })
          const isActive = pathname === href || pathname.startsWith(`${href}/`)

          return (
            <Link
              key={tab.id}
              href={href}
              aria-label={tab.navigationLabel}
              title={tab.navigationLabel}
              className={cn(
                'zyc-touch zyc-ripple inline-flex shrink-0 items-center rounded-full border px-4 text-sm transition',
                isActive
                  ? 'border-white/16 bg-white/14 text-white'
                  : 'border-white/8 bg-white/4 text-white/60 hover:border-white/14 hover:bg-white/8 hover:text-white'
              )}
            >
              {tab.label}
            </Link>
          )
        })}
      </div>
    </div>
  )
}
