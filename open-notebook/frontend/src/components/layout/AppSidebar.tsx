'use client'

import { useEffect, useMemo, useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { usePathname, useSearchParams } from 'next/navigation'
import {
  BrainCircuit,
  ChevronLeft,
  Command,
  LayoutDashboard,
  FileText,
  FolderKanban,
  LayoutPanelLeft,
  LogOut,
  Menu,
  Bot,
  Plus,
  Settings,
} from 'lucide-react'

import { LanguageToggle } from '@/components/common/LanguageToggle'
import { ThemeToggle } from '@/components/common/ThemeToggle'
import { useAuth } from '@/lib/hooks/use-auth'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import { useTranslation } from '@/lib/hooks/use-translation'
import { buildAssistantUrl } from '@/lib/assistant-workspace'
import { useSidebarStore } from '@/lib/stores/sidebar-store'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Separator } from '@/components/ui/separator'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

const CREATE_ITEMS = [
  {
    id: 'source',
    icon: FileText,
  },
  {
    id: 'project',
    icon: FolderKanban,
  },
] as const

export function AppSidebar() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { logout } = useAuth()
  const { t } = useTranslation()
  const { isCollapsed, toggleCollapse } = useSidebarStore()
  const { openSourceDialog, openNotebookDialog } = useCreateDialogs()
  const [createMenuOpen, setCreateMenuOpen] = useState(false)
  const [isMac, setIsMac] = useState(true)

  useEffect(() => {
    setIsMac(navigator.platform.toLowerCase().includes('mac'))
  }, [])

  const navigation = useMemo(
    () => [
      {
        name: t.navigation.dashboard,
        href: '/dashboard',
        icon: LayoutDashboard,
        isActive: pathname === '/dashboard',
      },
      {
        name: t.assistant.knowledgeHub,
        href: buildAssistantUrl({ view: 'knowledge' }),
        icon: FolderKanban,
        isActive: pathname === '/assistant' && searchParams.get('view') === 'knowledge',
      },
      {
        name: t.assistant.workspace,
        href: buildAssistantUrl({ view: 'workspace' }),
        icon: LayoutPanelLeft,
        isActive:
          pathname === '/assistant' &&
          (!searchParams.get('view') || searchParams.get('view') === 'workspace'),
      },
      {
        name: t.assistant.memoryManager,
        href: buildAssistantUrl({ view: 'memory' }),
        icon: BrainCircuit,
        isActive: pathname === '/assistant' && searchParams.get('view') === 'memory',
      },
      {
        name: t.navigation.models,
        href: '/models',
        icon: Bot,
        isActive:
          pathname === '/models' || pathname?.startsWith('/models/') || pathname === '/settings/api-keys',
      },
      {
        name: t.navigation.settings,
        href: '/settings',
        icon: Settings,
        isActive:
          pathname === '/settings' || pathname?.startsWith('/settings/') || false,
      },
    ],
    [pathname, searchParams, t]
  )

  const handleCreateSelection = (target: (typeof CREATE_ITEMS)[number]['id']) => {
    setCreateMenuOpen(false)
    if (target === 'source') {
      openSourceDialog()
      return
    }
    openNotebookDialog()
  }

  const handleOpenCommandPalette = () => {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('command-palette:toggle'))
    }
  }

  return (
    <TooltipProvider delayDuration={0}>
      <div
        className={cn(
          'app-sidebar flex h-full flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300',
          isCollapsed ? 'w-16' : 'w-64'
        )}
      >
        <div
          className={cn(
            'group flex h-16 items-center',
            isCollapsed ? 'justify-center px-2' : 'justify-between px-4'
          )}
        >
          {isCollapsed ? (
            <div className="relative flex w-full items-center justify-center">
              <Image
                src="/logo.svg"
                alt={t.common.appName}
                width={32}
                height={32}
                className="transition-opacity group-hover:opacity-0"
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleCollapse}
                className="absolute opacity-0 transition-opacity group-hover:opacity-100"
              >
                <Menu className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <Image src="/logo.svg" alt={t.common.appName} width={32} height={32} />
                <span className="text-base font-medium text-sidebar-foreground">
                  {t.common.appName}
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleCollapse}
                className="text-sidebar-foreground hover:bg-sidebar-accent"
                data-testid="sidebar-toggle"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>

        <div className={cn('px-3', isCollapsed && 'px-2')}>
          <DropdownMenu open={createMenuOpen} onOpenChange={setCreateMenuOpen}>
            {isCollapsed ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="default"
                      size="sm"
                      className="w-full justify-center px-2"
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                </TooltipTrigger>
                <TooltipContent side="right">{t.common.create}</TooltipContent>
              </Tooltip>
            ) : (
              <DropdownMenuTrigger asChild>
                <Button variant="default" size="sm" className="w-full justify-start">
                  <Plus className="mr-2 h-4 w-4" />
                  {t.common.create}
                </Button>
              </DropdownMenuTrigger>
            )}

            <DropdownMenuContent
              align={isCollapsed ? 'end' : 'start'}
              side={isCollapsed ? 'right' : 'bottom'}
              className="w-48"
            >
              {CREATE_ITEMS.map((item) => (
                <DropdownMenuItem
                  key={item.id}
                  onSelect={(event) => {
                    event.preventDefault()
                    handleCreateSelection(item.id)
                  }}
                  className="gap-2"
                >
                  <item.icon className="h-4 w-4" />
                  {item.id === 'source' ? t.common.source : t.assistant.createProject}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <nav className={cn('flex-1 space-y-1 px-3 py-4', isCollapsed && 'px-2')}>
          {navigation.map((item) => {
            const button = (
              <Button
                variant={item.isActive ? 'secondary' : 'ghost'}
                className={cn(
                  'sidebar-menu-item w-full gap-3 text-sidebar-foreground',
                  item.isActive && 'bg-sidebar-accent text-sidebar-accent-foreground',
                  isCollapsed ? 'justify-center px-2' : 'justify-start'
                )}
              >
                <item.icon className="h-4 w-4" />
                {!isCollapsed && <span>{item.name}</span>}
              </Button>
            )

            if (isCollapsed) {
              return (
                <Tooltip key={item.name}>
                  <TooltipTrigger asChild>
                    <Link href={item.href}>{button}</Link>
                  </TooltipTrigger>
                  <TooltipContent side="right">{item.name}</TooltipContent>
                </Tooltip>
              )
            }

            return (
              <Link key={item.name} href={item.href}>
                {button}
              </Link>
            )
          })}
        </nav>

        <div className={cn('space-y-2 border-t border-sidebar-border p-3', isCollapsed && 'px-2')}>
          {!isCollapsed ? (
            <button
              type="button"
              className="w-full rounded-md border border-sidebar-border bg-sidebar px-3 py-2 text-left text-xs text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent"
              onClick={handleOpenCommandPalette}
            >
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Command className="h-3 w-3" />
                  {t.common.quickActions}
                </span>
                <kbd className="inline-flex h-5 items-center rounded border bg-muted px-1.5 font-mono text-[10px] text-muted-foreground">
                  {isMac ? '⌘K' : 'Ctrl+K'}
                </kbd>
              </div>
              <p className="mt-1 text-[10px] text-sidebar-foreground/50">
                {t.common.quickActionsDesc}
              </p>
            </button>
          ) : (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  className="w-full justify-center"
                  onClick={handleOpenCommandPalette}
                >
                  <Command className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">{t.common.quickActions}</TooltipContent>
            </Tooltip>
          )}

          <Separator />

          <div className={cn('flex flex-col gap-2', isCollapsed && 'items-center')}>
            {isCollapsed ? (
              <>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <ThemeToggle iconOnly />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="right">{t.common.theme}</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <LanguageToggle iconOnly />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="right">{t.common.language}</TooltipContent>
                </Tooltip>
              </>
            ) : (
              <>
                <ThemeToggle />
                <LanguageToggle />
              </>
            )}
          </div>

          {isCollapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  className="w-full justify-center sidebar-menu-item"
                  onClick={logout}
                  aria-label={t.common.signOut}
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">{t.common.signOut}</TooltipContent>
            </Tooltip>
          ) : (
            <Button
              type="button"
              variant="outline"
              className="w-full justify-start gap-3 sidebar-menu-item"
              onClick={logout}
            >
              <LogOut className="h-4 w-4" />
              {t.common.signOut}
            </Button>
          )}
        </div>
      </div>
    </TooltipProvider>
  )
}
