'use client'

import { faCheck, faPen, faSnowflake, faTrash, faWaveSquare } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Button } from '@/components/ui/button'
import type { ZycMemoryItem } from '@/lib/zhiyancang/types'

import { DecayCurve } from './decay-curve'

interface MemoryCardProps {
  item: ZycMemoryItem
  onAccept?: (item: ZycMemoryItem) => void
  onFreeze?: (item: ZycMemoryItem) => void
  onDeprecate?: (item: ZycMemoryItem) => void
  onEdit?: (item: ZycMemoryItem) => void
  onDelete?: (item: ZycMemoryItem) => void
  disabled?: boolean
}

export function MemoryCard({
  item,
  onAccept,
  onFreeze,
  onDeprecate,
  onEdit,
  onDelete,
  disabled = false,
}: MemoryCardProps) {
  return (
    <div className="rounded-[22px] border border-white/8 bg-white/4 px-4 py-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-white/50">
          {item.scope}
        </span>
        <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-white/50">
          {Math.round(item.confidence * 100)}%
        </span>
      </div>
      <p className="mt-4 text-sm leading-7 text-white/68">{item.content}</p>
      <div className="mt-4 text-xs text-white/44">{item.source}</div>
      <div className="mt-3 text-xs text-white/42">{item.status}</div>
      {item.bucket === 'decayed' ? (
        <div className="mt-3 rounded-2xl border border-white/8 bg-black/18 px-3 py-3">
          <DecayCurve values={item.decay} />
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        {item.status === 'draft' ? (
          <Button
            type="button"
            size="sm"
            disabled={disabled}
            onClick={() => onAccept?.(item)}
            className="rounded-full bg-white text-zinc-950 hover:bg-white/92"
          >
            <FontAwesomeIcon icon={faCheck} className="mr-2 text-xs" />
            Accept
          </Button>
        ) : null}
        {item.status !== 'frozen' ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={disabled}
            onClick={() => onFreeze?.(item)}
            className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
          >
            <FontAwesomeIcon icon={faSnowflake} className="mr-2 text-xs" />
            Freeze
          </Button>
        ) : null}
        {item.status !== 'deprecated' ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={disabled}
            onClick={() => onDeprecate?.(item)}
            className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
          >
            <FontAwesomeIcon icon={faWaveSquare} className="mr-2 text-xs" />
            Deprecate
          </Button>
        ) : null}
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={disabled}
          onClick={() => onEdit?.(item)}
          className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
        >
          <FontAwesomeIcon icon={faPen} className="mr-2 text-xs" />
          Edit
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={disabled}
          onClick={() => onDelete?.(item)}
          className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
        >
          <FontAwesomeIcon icon={faTrash} className="mr-2 text-xs" />
          Delete
        </Button>
      </div>
    </div>
  )
}
