'use client'

export function NextStepsList({ steps }: { steps: string[] }) {
  return (
    <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
      <div className="text-sm font-medium text-white">Next Steps</div>
      <div className="mt-4 space-y-3">
        {steps.map((step, index) => (
          <div key={step} className="flex gap-3 rounded-2xl border border-white/8 bg-white/4 px-4 py-3">
            <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-white/78">
              {index + 1}
            </div>
            <p className="text-sm leading-7 text-white/68">{step}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
