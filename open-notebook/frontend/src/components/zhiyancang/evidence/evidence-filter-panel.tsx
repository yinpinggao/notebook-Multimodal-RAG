'use client'

import { faFilter, faMagnifyingGlass } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import type { ZycEvidenceModel } from '@/lib/zhiyancang/types'
import { cn } from '@/lib/utils'

export function EvidenceFilterPanel({ evidence }: { evidence: ZycEvidenceModel }) {
  const { activeSearchMode, setActiveSearchMode } = useZycUIStore()

  return (
    <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
      <div className="flex items-center gap-3 text-sm font-medium text-white">
        <FontAwesomeIcon icon={faFilter} className="text-white/54" />
        Filter Panel
      </div>

      <label className="mt-4 flex items-center gap-3 rounded-2xl border border-white/8 bg-white/4 px-4 py-3">
        <FontAwesomeIcon icon={faMagnifyingGlass} className="text-white/40" />
        <input
          placeholder="Keyword, title, source..."
          className="zyc-underline-input w-full text-sm text-white placeholder:text-white/35 focus:outline-none"
        />
      </label>

      <div className="mt-5 text-xs uppercase tracking-[0.16em] text-white/38">Search Modes</div>
      <div className="mt-3 grid gap-2">
        {evidence.searchModes.map((mode) => (
          <button
            key={mode}
            type="button"
            onClick={() => setActiveSearchMode(mode)}
            className={cn(
              'rounded-2xl border px-4 py-3 text-left text-sm transition',
              activeSearchMode === mode
                ? 'border-[rgba(71,182,255,0.35)] bg-[rgba(71,182,255,0.12)] text-white'
                : 'border-white/8 bg-white/4 text-white/60 hover:border-white/14 hover:bg-white/8 hover:text-white'
            )}
          >
            {mode.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  )
}
