'use client'

import { faClockRotateLeft } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import type { ZycOverviewModel } from '@/lib/zhiyancang/types'

function RailSection({
  title,
  items,
}: {
  title: string
  items: ZycOverviewModel['recentEvidence']
}) {
  return (
    <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
      <div className="text-sm font-medium text-white">{title}</div>
      <div className="mt-3 space-y-3">
        {items.map((item) => (
          <div key={item.id} className="rounded-2xl border border-white/8 bg-black/18 px-4 py-3">
            <div className="text-sm font-medium text-white">{item.title}</div>
            <div className="mt-1 text-xs text-white/45">{item.meta}</div>
            <p className="mt-2 text-sm leading-6 text-white/62">{item.detail}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export function OverviewStickyRail({ overview }: { overview: ZycOverviewModel }) {
  return (
    <aside className="sticky top-28 space-y-4">
      <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
        <div className="flex items-center gap-3 text-sm font-medium text-white">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/8 text-white/72">
            <FontAwesomeIcon icon={faClockRotateLeft} />
          </div>
          Recent Signals
        </div>

        <div className="mt-4 space-y-4">
          <RailSection title="Evidence" items={overview.recentEvidence} />
          <RailSection title="Memory" items={overview.recentMemory} />
          <RailSection title="Runs" items={overview.recentRuns} />
          <RailSection title="Artifacts" items={overview.artifacts} />
        </div>
      </div>
    </aside>
  )
}
