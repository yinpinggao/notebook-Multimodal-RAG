'use client'

import { PROJECT_PHASES, type ProjectPhase } from '@/lib/zhiyancang/types'
import { cn } from '@/lib/utils'

export function PhaseProgress({ currentPhase }: { currentPhase: ProjectPhase }) {
  const currentIndex = PROJECT_PHASES.findIndex((phase) => phase.id === currentPhase)

  return (
    <div className="zyc-glass rounded-[24px] px-4 py-4">
      <div className="grid gap-3 md:grid-cols-6">
        {PROJECT_PHASES.map((phase, index) => {
          const isPast = index <= currentIndex

          return (
            <div
              key={phase.id}
              className={cn(
                'rounded-2xl border px-4 py-3 transition',
                isPast
                  ? 'border-white/14 bg-white/10 text-white'
                  : 'border-white/8 bg-white/3 text-white/46'
              )}
              style={isPast ? { boxShadow: `inset 0 2px 0 ${phase.accent}` } : undefined}
            >
              <div className="text-[11px] uppercase tracking-[0.16em] text-white/40">
                Step {index + 1}
              </div>
              <div className="mt-2 text-sm font-medium">{phase.label}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
