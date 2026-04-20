'use client'

import type { ReactNode } from 'react'

export function ShowcaseSectionFrame({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <section className="zyc-panel rounded-[28px] px-5 py-5 shadow-zyc-soft lg:px-6">
      <div className="mb-5">
        <div className="text-xs uppercase tracking-[0.16em] text-white/40">{title}</div>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-white/62">{description}</p>
      </div>
      {children}
    </section>
  )
}
