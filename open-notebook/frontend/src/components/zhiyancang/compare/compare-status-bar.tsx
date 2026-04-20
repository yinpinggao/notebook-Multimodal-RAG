'use client'

import { cn } from '@/lib/utils'
import type { RunStatus } from '@/lib/zhiyancang/types'

const STATUSES: RunStatus[] = ['queued', 'running', 'completed', 'failed']

export function CompareStatusBar({ status }: { status: RunStatus }) {
  const activeIndex = STATUSES.findIndex((item) => item === status)

  return (
    <div className="rounded-[24px] border border-white/8 bg-white/4 p-4">
      <div className="grid gap-3 md:grid-cols-4">
        {STATUSES.map((item, index) => (
          <div
            key={item}
            className={cn(
              'rounded-2xl border px-4 py-3 text-sm capitalize transition',
              index <= activeIndex
                ? 'border-[rgba(240,174,67,0.3)] bg-[rgba(240,174,67,0.14)] text-white'
                : 'border-white/8 bg-black/14 text-white/42'
            )}
          >
            {item}
          </div>
        ))}
      </div>
    </div>
  )
}
