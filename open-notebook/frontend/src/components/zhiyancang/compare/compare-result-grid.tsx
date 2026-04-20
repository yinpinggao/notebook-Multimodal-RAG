'use client'

import type { ZycCompareModel } from '@/lib/zhiyancang/types'

export function CompareResultGrid({ compare }: { compare: ZycCompareModel }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {compare.results.map((group) => (
        <div
          key={group.id}
          className="rounded-[24px] border border-white/8 px-5 py-5 shadow-zyc-soft"
          style={{ backgroundColor: group.accent }}
        >
          <div className="text-base font-semibold text-white">{group.title}</div>
          <div className="mt-4 space-y-3">
            {group.items.map((item) => (
              <div key={item} className="rounded-2xl border border-white/10 bg-black/16 px-4 py-3 text-sm leading-7 text-white/72">
                {item}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
