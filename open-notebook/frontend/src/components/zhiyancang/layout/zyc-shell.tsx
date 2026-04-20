'use client'

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'

import { GlobalHeader } from '@/components/zhiyancang/layout/global-header'
import { GlobalTabs } from '@/components/zhiyancang/layout/global-tabs'
import { MobileDrawer } from '@/components/zhiyancang/layout/mobile-drawer'
import { buildGlobalPath } from '@/lib/project-paths'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import type { GlobalSection } from '@/lib/zhiyancang/types'

function resolveGlobalSection(pathname: string): GlobalSection {
  if (pathname.startsWith(buildGlobalPath('library'))) {
    return 'library'
  }

  if (pathname.startsWith(buildGlobalPath('system'))) {
    return 'system'
  }

  return 'projects'
}

export function ZycShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const {
    mobileNavOpen,
    setActiveGlobalSection,
    setMobileNavOpen,
  } = useZycUIStore()

  useEffect(() => {
    setActiveGlobalSection(resolveGlobalSection(pathname))
  }, [pathname, setActiveGlobalSection])

  return (
    <div className="zyc-shell min-h-screen">
      <GlobalHeader onOpenMobileNav={() => setMobileNavOpen(true)} />
      <main className="mx-auto flex max-w-[1440px] flex-col gap-6 px-4 py-6 lg:px-6">
        {children}
      </main>

      <MobileDrawer
        open={mobileNavOpen}
        onOpenChange={setMobileNavOpen}
        side="bottom"
        title="ZhiyanCang Navigation"
        description="Move between the global layers."
      >
        <GlobalTabs />
      </MobileDrawer>
    </div>
  )
}
