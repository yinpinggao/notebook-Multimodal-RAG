'use client'

import { useMemo } from 'react'

import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import type { ZycEvidenceModel } from '@/lib/zhiyancang/types'

import { EvidenceCard } from './evidence-card'

export function EvidenceMasonry({
  evidence,
  showAll = false,
}: {
  evidence: ZycEvidenceModel
  showAll?: boolean
}) {
  const { activeEvidenceType } = useZycUIStore()

  const filteredItems = useMemo(
    () =>
      showAll ? evidence.items : evidence.items.filter((item) => item.type === activeEvidenceType),
    [activeEvidenceType, evidence.items, showAll]
  )

  const items = filteredItems.length > 0 ? filteredItems : evidence.items

  return (
    <div className="zyc-masonry">
      {items.map((item) => (
        <EvidenceCard key={item.id} item={item} />
      ))}
    </div>
  )
}
