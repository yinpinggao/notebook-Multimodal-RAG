'use client'

import type { ZycMemoryItem } from '@/lib/zhiyancang/types'

import { MemoryCard } from './memory-card'

const BUCKET_LABELS = {
  inbox: 'Inbox',
  stable: 'Stable',
  frozen: 'Frozen',
  decayed: 'Decayed',
}

interface MemorySectionBoardProps {
  items: ZycMemoryItem[]
  onAccept?: (item: ZycMemoryItem) => void
  onFreeze?: (item: ZycMemoryItem) => void
  onDeprecate?: (item: ZycMemoryItem) => void
  onEdit?: (item: ZycMemoryItem) => void
  onDelete?: (item: ZycMemoryItem) => void
  disabled?: boolean
}

export function MemorySectionBoard({
  items,
  onAccept,
  onFreeze,
  onDeprecate,
  onEdit,
  onDelete,
  disabled = false,
}: MemorySectionBoardProps) {
  return (
    <div className="grid gap-4 xl:grid-cols-4">
      {Object.entries(BUCKET_LABELS).map(([bucket, label]) => {
        const bucketItems = items.filter((item) => item.bucket === bucket)

        return (
          <section key={bucket} className="zyc-panel rounded-[24px] px-4 py-4 shadow-zyc-soft">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-medium text-white">{label}</div>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/48">
                {bucketItems.length}
              </span>
            </div>

            <div className="mt-4 space-y-4">
              {bucketItems.map((item) => (
                <MemoryCard
                  key={item.id}
                  item={item}
                  onAccept={onAccept}
                  onFreeze={onFreeze}
                  onDeprecate={onDeprecate}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  disabled={disabled}
                />
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}
