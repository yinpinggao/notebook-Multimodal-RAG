'use client'

import Image from 'next/image'

export function ScreenshotStrip({
  items,
}: {
  items: Array<{ id: string; label: string; image: string }>
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {items.map((item) => (
        <div key={item.id} className="overflow-hidden rounded-[24px] border border-white/8 bg-[#17181b]/92 shadow-zyc-soft">
          <div className="relative h-52">
            <Image src={item.image} alt={item.label} fill className="object-cover" sizes="(max-width: 1024px) 100vw, 40vw" />
          </div>
          <div className="px-4 py-4 text-sm text-white/68">{item.label}</div>
        </div>
      ))}
    </div>
  )
}
