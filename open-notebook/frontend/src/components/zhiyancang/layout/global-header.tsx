'use client'

import Link from 'next/link'
import {
  faBarsStaggered,
  faBookOpen,
  faBrain,
  faChevronDown,
  faFolderTree,
  faGear,
  faGrip,
} from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { GlobalSearch } from '@/components/zhiyancang/layout/global-search'
import { GlobalTabs } from '@/components/zhiyancang/layout/global-tabs'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface GlobalHeaderProps {
  onOpenMobileNav: () => void
}

const QUICK_LINKS = [
  { label: 'Projects', href: '/projects', icon: faFolderTree },
  { label: 'Library', href: '/library', icon: faBookOpen },
  { label: 'System', href: '/system', icon: faGear },
]

export function GlobalHeader({ onOpenMobileNav }: GlobalHeaderProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-white/8 bg-[#121212]/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-4 px-4 py-3 lg:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenMobileNav}
            className="zyc-touch zyc-ripple inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white/80 transition hover:bg-white/9 lg:hidden"
            aria-label="Open navigation"
          >
            <FontAwesomeIcon icon={faBarsStaggered} />
          </button>

          <Link href="/projects" className="flex min-w-0 items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/8 text-white shadow-zyc-soft">
              <FontAwesomeIcon icon={faBrain} className="text-[15px]" />
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold tracking-[0.08em] text-white/70">
                ZhiyanCang
              </div>
              <div className="truncate text-base font-semibold text-white">
                Research OS
              </div>
            </div>
          </Link>

          <div className="hidden flex-1 lg:block">
            <GlobalSearch />
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                className="zyc-touch rounded-full border-white/10 bg-white/5 px-4 text-white hover:bg-white/10 hover:text-white"
              >
                <FontAwesomeIcon icon={faGrip} className="mr-2" />
                Quick Links
                <FontAwesomeIcon icon={faChevronDown} className="ml-2 text-xs text-white/50" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="w-56 rounded-2xl border-white/10 bg-[#17181b]/96 p-2 text-zinc-50"
            >
              {QUICK_LINKS.map((item) => (
                <DropdownMenuItem key={item.href} asChild>
                  <Link
                    href={item.href}
                    className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-white/80 outline-none hover:bg-white/8 hover:text-white"
                  >
                    <FontAwesomeIcon icon={item.icon} className="text-white/55" />
                    {item.label}
                  </Link>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className="lg:hidden">
          <GlobalSearch />
        </div>

        <div className="hidden lg:flex">
          <GlobalTabs />
        </div>
      </div>
    </header>
  )
}
