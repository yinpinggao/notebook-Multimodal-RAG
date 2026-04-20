'use client'

import { faMagnifyingGlass, faSliders } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

export function GlobalSearch() {
  return (
    <div className="zyc-glass flex h-11 min-w-0 items-center gap-3 rounded-full px-4 py-2 text-sm text-white/80">
      <FontAwesomeIcon icon={faMagnifyingGlass} className="text-white/50" />
      <input
        aria-label="Search ZhiyanCang"
        placeholder="Search projects, evidence, memory..."
        className="zyc-underline-input zyc-touch min-w-0 flex-1 text-sm text-white placeholder:text-white/35 focus:outline-none"
      />
      <button
        type="button"
        className="zyc-touch zyc-ripple inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/6 text-white/70 transition hover:bg-white/10 hover:text-white"
      >
        <FontAwesomeIcon icon={faSliders} />
      </button>
    </div>
  )
}
