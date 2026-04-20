'use client'

import { getPhaseMeta, type ProjectPhase } from '@/lib/zhiyancang/types'

export function PhaseBadge({ phase }: { phase: ProjectPhase }) {
  const meta = getPhaseMeta(phase)

  return (
    <span
      className="inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium text-white/82"
      style={{
        borderColor: meta.accent,
        backgroundColor: `${meta.accent.slice(0, -4)}0.12)`,
      }}
    >
      {meta.label}
    </span>
  )
}
