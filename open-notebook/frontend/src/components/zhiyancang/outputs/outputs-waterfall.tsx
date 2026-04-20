'use client'

import type { ZycOutputItem } from '@/lib/zhiyancang/types'

import { OutputCard } from './output-card'

export function OutputsWaterfall({ items }: { items: ZycOutputItem[] }) {
  return (
    <div className="zyc-waterfall">
      {items.map((item) => (
        <OutputCard key={item.id} item={item} />
      ))}
    </div>
  )
}
