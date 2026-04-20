'use client'

import type { ZycOutputItem } from '@/lib/zhiyancang/types'

export function OutputCard({ item }: { item: ZycOutputItem }) {
  return (
    <article className="zyc-hover-lift overflow-hidden rounded-[24px] border border-white/8 bg-[#17181b]/92 shadow-zyc-soft">
      <div className="border-b border-white/8 bg-[rgba(83,194,123,0.08)] px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-base font-semibold text-white">{item.title}</div>
            <div className="mt-1 text-xs text-white/48">{item.template}</div>
          </div>
          <span className="rounded-full border border-white/10 px-3 py-1 text-xs capitalize text-white/52">
            {item.status}
          </span>
        </div>
      </div>

      <div className="px-4 py-4">
        <p className="text-sm leading-7 text-white/68">{item.preview}</p>
      </div>
    </article>
  )
}
