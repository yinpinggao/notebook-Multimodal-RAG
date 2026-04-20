'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { useTranslation } from '@/lib/hooks/use-translation'
import { buildGlobalPath } from '@/lib/project-paths'
import { type GlobalSection } from '@/lib/zhiyancang/types'
import { cn } from '@/lib/utils'

export function GlobalTabs() {
  const pathname = usePathname()
  const { t } = useTranslation()

  const globalTabs: Array<{ id: GlobalSection; label: string; navigationLabel: string }> = [
    {
      id: 'projects',
      label: t.zhiyancang.projects,
      navigationLabel: t.navigation.projects,
    },
    {
      id: 'library',
      label: t.zhiyancang.library,
      navigationLabel: t.navigation.library,
    },
    {
      id: 'system',
      label: t.zhiyancang.system,
      navigationLabel: t.common.system,
    },
  ]

  return (
    <nav className="flex flex-wrap items-center gap-2">
      {globalTabs.map((tab) => {
        const href = buildGlobalPath(tab.id)
        const isActive = pathname === href || pathname.startsWith(`${href}/`)

        return (
          <Link
            key={tab.id}
            href={href}
            aria-label={tab.navigationLabel}
            title={tab.navigationLabel}
            className={cn(
              'zyc-touch zyc-ripple inline-flex items-center rounded-full border px-4 text-sm transition',
              isActive
                ? 'border-white/18 bg-white/12 text-white shadow-zyc-soft'
                : 'border-white/8 bg-white/4 text-white/60 hover:border-white/15 hover:bg-white/8 hover:text-white'
            )}
          >
            {tab.label}
          </Link>
        )
      })}
    </nav>
  )
}
