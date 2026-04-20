'use client'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import type { ZycCompareModel } from '@/lib/zhiyancang/types'

export function CompareSourceSelector({ compare }: { compare: ZycCompareModel }) {
  const {
    selectedCompareSourceA,
    selectedCompareSourceB,
    setSelectedCompareSourceA,
    setSelectedCompareSourceB,
  } = useZycUIStore()

  return (
    <div className="grid gap-3 md:grid-cols-2">
      <Select value={selectedCompareSourceA} onValueChange={setSelectedCompareSourceA}>
        <SelectTrigger className="h-12 rounded-[20px] border-white/10 bg-white/6 text-white">
          <SelectValue placeholder="Select source A" />
        </SelectTrigger>
        <SelectContent className="rounded-[20px] border-white/10 bg-[#18191d]/96 text-white">
          {compare.sources.map((source) => (
            <SelectItem key={source.id} value={source.id}>
              {source.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={selectedCompareSourceB} onValueChange={setSelectedCompareSourceB}>
        <SelectTrigger className="h-12 rounded-[20px] border-white/10 bg-white/6 text-white">
          <SelectValue placeholder="Select source B" />
        </SelectTrigger>
        <SelectContent className="rounded-[20px] border-white/10 bg-[#18191d]/96 text-white">
          {compare.sources.map((source) => (
            <SelectItem key={source.id} value={source.id}>
              {source.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
