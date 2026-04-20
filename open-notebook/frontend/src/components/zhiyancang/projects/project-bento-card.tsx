'use client'

import Image from 'next/image'
import Link from 'next/link'
import {
  faArrowUpRightFromSquare,
  faFileWaveform,
  faLayerGroup,
  faMemory,
  faWaveSquare,
} from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { PhaseBadge } from '@/components/zhiyancang/projects/phase-badge'
import { buildProjectPath } from '@/lib/project-paths'
import { getPhaseMeta } from '@/lib/zhiyancang/types'
import type { ZycProjectCard } from '@/lib/zhiyancang/types'

export function ProjectBentoCard({ project }: { project: ZycProjectCard }) {
  const phaseMeta = getPhaseMeta(project.phase)

  return (
    <Link
      href={buildProjectPath({ projectId: project.id, section: 'overview' })}
      className="zyc-hover-lift block overflow-hidden rounded-[24px] border border-white/8 bg-[#17181b]/90 shadow-zyc-soft"
      style={{ boxShadow: `inset 0 2px 0 ${phaseMeta.accent}` }}
    >
      <div className="relative h-48 overflow-hidden border-b border-white/8">
        <Image
          src={project.heroImage}
          alt={project.name}
          fill
          className="object-cover"
          sizes="(max-width: 768px) 100vw, 33vw"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#121212] via-[#121212]/30 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 flex items-end justify-between px-5 pb-5">
          <div className="space-y-2">
            <div className="text-xs uppercase tracking-[0.16em] text-white/55">
              {project.badge}
            </div>
            <h2 className="text-2xl font-semibold text-white">{project.name}</h2>
          </div>
          <div className="rounded-full border border-white/10 bg-black/25 p-3 text-white/78">
            <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
          </div>
        </div>
      </div>

      <div className="space-y-5 px-5 py-5">
        <div className="flex flex-wrap items-center gap-2">
          <PhaseBadge phase={project.phase} />
          <span className="rounded-full border border-white/8 bg-white/4 px-3 py-1 text-xs text-white/55">
            {project.runStatus}
          </span>
          <span className="text-xs text-white/45">{project.updatedAt}</span>
        </div>

        <p className="text-sm leading-7 text-white/66">{project.summary}</p>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <div className="flex items-center gap-2 text-xs text-white/45">
              <FontAwesomeIcon icon={faFileWaveform} />
              Evidence
            </div>
            <div className="mt-2 text-2xl font-semibold text-white">{project.evidenceCount}</div>
          </div>
          <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <div className="flex items-center gap-2 text-xs text-white/45">
              <FontAwesomeIcon icon={faMemory} />
              Memory
            </div>
            <div className="mt-2 text-2xl font-semibold text-white">{project.memoryCount}</div>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <div className="flex items-center gap-2 text-xs text-white/45">
              <FontAwesomeIcon icon={faLayerGroup} />
              Latest Output
            </div>
            <div className="mt-2 text-sm font-medium text-white">{project.latestOutput}</div>
          </div>
          <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
            <div className="flex items-center gap-2 text-xs text-white/45">
              <FontAwesomeIcon icon={faWaveSquare} />
              Run Status
            </div>
            <div className="mt-2 text-sm font-medium capitalize text-white">{project.runStatus}</div>
          </div>
        </div>
      </div>
    </Link>
  )
}
