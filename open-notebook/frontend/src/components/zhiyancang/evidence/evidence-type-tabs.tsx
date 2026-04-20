'use client'

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import type { EvidenceType } from '@/lib/zhiyancang/types'

const TAB_ITEMS: Array<{ id: EvidenceType; label: string }> = [
  { id: 'docs', label: 'Docs' },
  { id: 'web', label: 'Web' },
  { id: 'images', label: 'Images' },
  { id: 'audio', label: 'Audio' },
  { id: 'visual', label: 'Visual Evidence' },
]

export function EvidenceTypeTabs() {
  const { activeEvidenceType, setActiveEvidenceType } = useZycUIStore()

  return (
    <Tabs value={activeEvidenceType} onValueChange={(value) => setActiveEvidenceType(value as EvidenceType)}>
      <TabsList className="w-full flex-wrap justify-start rounded-[22px] border-white/8 bg-white/4 p-2">
        {TAB_ITEMS.map((tab) => (
          <TabsTrigger
            key={tab.id}
            value={tab.id}
            className="zyc-touch rounded-[18px] border-white/0 px-4 text-white/60 data-[state=active]:border-white/10 data-[state=active]:bg-white/10 data-[state=active]:text-white"
          >
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  )
}
