'use client'

import Link from 'next/link'
import {
  faArrowRight,
  faFlaskVial,
  faGear,
  faLayerGroup,
  faMicrochip,
} from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useZycSystem } from '@/lib/hooks/use-zyc-global'
import { formatApiError } from '@/lib/utils/error-handler'

const ICON_MAP = {
  models: faMicrochip,
  settings: faGear,
  jobs: faLayerGroup,
  evals: faFlaskVial,
}

export default function SystemPage() {
  const { data, error, isLoading } = useZycSystem()

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>System unavailable</AlertTitle>
        <AlertDescription>{formatApiError(error)}</AlertDescription>
      </Alert>
    )
  }

  if (isLoading || !data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="zyc-glass rounded-[28px] px-5 py-6 lg:px-7">
        <div className="text-xs uppercase tracking-[0.16em] text-white/40">Global Layer / System</div>
        <h1 className="mt-3 text-3xl font-semibold text-white lg:text-5xl">
          Models, settings, jobs, and evals in one low-clutter control plane.
        </h1>
      </section>

      <section className="grid gap-5 lg:grid-cols-2 xl:grid-cols-4">
        {data.cards.map((card) => (
          <Link
            key={card.id}
            href={card.href}
            className="zyc-hover-lift overflow-hidden rounded-[24px] border border-white/8 bg-[#17181b]/92 px-5 py-5 shadow-zyc-soft"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/8 text-white/70">
              <FontAwesomeIcon icon={ICON_MAP[card.id as keyof typeof ICON_MAP]} />
            </div>
            <div className="mt-5 text-lg font-semibold text-white">{card.title}</div>
            <p className="mt-3 text-sm leading-7 text-white/62">{card.description}</p>
            <div className="mt-4 text-xs uppercase tracking-[0.16em] text-white/40">{card.health}</div>
          </Link>
        ))}
      </section>

      <section className="zyc-panel rounded-[28px] px-5 py-5 shadow-zyc-soft">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-medium text-white">System Health</div>
            <p className="mt-1 text-sm text-white/52">
              High-signal status checks for the research OS control plane.
            </p>
          </div>
          <Link href="/settings" className="text-sm text-white/68 hover:text-white">
            Inspect settings
            <FontAwesomeIcon icon={faArrowRight} className="ml-2" />
          </Link>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {data.health.map((item) => (
            <div key={item.id} className="rounded-[22px] border border-white/8 bg-white/4 px-4 py-4">
              <div className="text-xs uppercase tracking-[0.16em] text-white/40">{item.label}</div>
              <div className="mt-3 text-xl font-semibold text-white">{item.value}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
