'use client'

import { ChevronDown, PanelLeft } from 'lucide-react'
import type { CSSProperties, ReactNode } from 'react'

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { useMediaQuery } from '@/lib/hooks/use-media-query'
import { cn } from '@/lib/utils'

interface PageContainerProps {
  children: ReactNode
  className?: string
}

export function PageContainer({ children, className }: PageContainerProps) {
  return (
    <div className={cn('mx-auto w-full max-w-[1280px] space-y-6', className)}>
      {children}
    </div>
  )
}

interface PageHeaderProps {
  eyebrow?: ReactNode
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  meta?: ReactNode
  className?: string
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  meta,
  className,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        'flex flex-col gap-4 border-b border-border/70 pb-5 lg:flex-row lg:items-start lg:justify-between',
        className
      )}
    >
      <div className="min-w-0 space-y-3">
        {eyebrow ? <div className="flex flex-wrap items-center gap-2">{eyebrow}</div> : null}
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
          {description ? (
            <p className="max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p>
          ) : null}
        </div>
        {meta ? <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">{meta}</div> : null}
      </div>

      {actions ? <div className="flex flex-wrap gap-2 lg:justify-end">{actions}</div> : null}
    </header>
  )
}

interface AutoGridProps {
  children: ReactNode
  className?: string
  minItemWidth?: number
}

export function AutoGrid({
  children,
  className,
  minItemWidth = 280,
}: AutoGridProps) {
  return (
    <div
      className={cn('grid gap-4', className)}
      style={{
        gridTemplateColumns: `repeat(auto-fit, minmax(${minItemWidth}px, 1fr))`,
      }}
    >
      {children}
    </div>
  )
}

export function ActionGrid(props: AutoGridProps) {
  return <AutoGrid {...props} />
}

interface CollapsibleRailProps {
  title: ReactNode
  description?: ReactNode
  badge?: ReactNode
  children: ReactNode
  defaultOpen?: boolean
  className?: string
  contentClassName?: string
}

export function CollapsibleRail({
  title,
  description,
  badge,
  children,
  defaultOpen = true,
  className,
  contentClassName,
}: CollapsibleRailProps) {
  return (
    <Collapsible defaultOpen={defaultOpen} className={className}>
      <div className="rounded-md border border-border/70 bg-background">
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <PanelLeft className="h-4 w-4 text-muted-foreground" />
                <span>{title}</span>
              </div>
              {description ? (
                <div className="text-xs leading-5 text-muted-foreground">{description}</div>
              ) : null}
            </div>
            <div className="flex items-center gap-2">
              {badge}
              <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform data-[state=open]:rotate-180" />
            </div>
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent className={cn('border-t border-border/70 px-0 py-0', contentClassName)}>
          {children}
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

interface DetailSplitLayoutProps {
  rail: ReactNode
  detail: ReactNode
  railTitle: ReactNode
  railDescription?: ReactNode
  railBadge?: ReactNode
  defaultRailOpen?: boolean
  railWidth?: string
  detailWidth?: string
  className?: string
}

export function DetailSplitLayout({
  rail,
  detail,
  railTitle,
  railDescription,
  railBadge,
  defaultRailOpen = true,
  railWidth = 'minmax(320px, 0.95fr)',
  detailWidth = 'minmax(0, 1.55fr)',
  className,
}: DetailSplitLayoutProps) {
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const desktopStyle: CSSProperties = {
    gridTemplateColumns: `${railWidth} ${detailWidth}`,
  }

  if (isDesktop) {
    return (
      <div className={cn('grid min-w-0 gap-4', className)} style={desktopStyle}>
        <div className="min-w-0 space-y-4">{rail}</div>
        <div className="min-w-0">{detail}</div>
      </div>
    )
  }

  return (
    <div className={cn('space-y-4', className)}>
      <CollapsibleRail
        title={railTitle}
        description={railDescription}
        badge={railBadge}
        defaultOpen={defaultRailOpen}
      >
        <div className="space-y-4 p-4">{rail}</div>
      </CollapsibleRail>
      <div className="min-w-0">{detail}</div>
    </div>
  )
}
