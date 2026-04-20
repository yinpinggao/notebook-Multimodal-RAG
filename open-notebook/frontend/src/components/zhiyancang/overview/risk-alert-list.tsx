'use client'

import { faTriangleExclamation } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

export function RiskAlertList({ items }: { items: string[] }) {
  return (
    <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
      <div className="flex items-center gap-3 text-sm font-medium text-white">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[rgba(240,174,67,0.16)] text-[#f0ae43]">
          <FontAwesomeIcon icon={faTriangleExclamation} />
        </div>
        Risk Alerts
      </div>

      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div key={item} className="rounded-2xl border border-white/8 bg-white/4 px-4 py-3">
            <p className="text-sm leading-7 text-white/70">{item}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
