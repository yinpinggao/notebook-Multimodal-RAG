'use client'

import Image from 'next/image'
import { faArrowUpRightFromSquare } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import type { ZycEvidenceItem } from '@/lib/zhiyancang/types'

export function EvidenceCard({ item }: { item: ZycEvidenceItem }) {
  return (
    <article className="zyc-hover-lift overflow-hidden rounded-[24px] border border-white/8 bg-[#17181b]/92 shadow-zyc-soft">
      <div className="relative h-44 overflow-hidden">
        <Image src={item.thumbnail} alt={item.title} fill className="object-cover" sizes="(max-width: 1024px) 100vw, 25vw" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#121212] via-transparent to-transparent" />
        <div className="absolute left-4 top-4 rounded-full border border-white/12 bg-black/30 px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-white/70">
          {item.type}
        </div>
      </div>

      <div className="space-y-4 px-4 py-4">
        <div>
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-base font-semibold text-white">{item.title}</h3>
            <FontAwesomeIcon icon={faArrowUpRightFromSquare} className="mt-1 text-white/45" />
          </div>
          <div className="mt-1 text-xs text-white/45">{item.source}</div>
        </div>

        <p className="text-sm leading-7 text-white/64">{item.snippet}</p>

        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-white/10 bg-white/4 px-3 py-1 text-xs text-white/52">
            {item.confidence}
          </span>
          {item.actions.map((action) => (
            <span key={action} className="rounded-full border border-white/8 px-3 py-1 text-xs text-white/46">
              {action}
            </span>
          ))}
        </div>
      </div>
    </article>
  )
}
