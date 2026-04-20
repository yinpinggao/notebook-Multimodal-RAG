'use client'

import type { ReactNode } from 'react'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

interface MobileDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  children: ReactNode
  side?: 'left' | 'right' | 'bottom'
}

const SIDE_CLASS_NAMES: Record<NonNullable<MobileDrawerProps['side']>, string> = {
  left: 'left-0 top-0 h-full max-w-[24rem] translate-x-0 translate-y-0 rounded-none border-r border-white/10 bg-[#17181b]/96 p-0',
  right:
    'left-auto right-0 top-0 h-full max-w-[24rem] translate-x-0 translate-y-0 rounded-none border-l border-white/10 bg-[#17181b]/96 p-0',
  bottom:
    'left-1/2 top-auto bottom-0 max-h-[82vh] w-full max-w-[calc(100%-1rem)] -translate-x-1/2 translate-y-0 rounded-t-2xl rounded-b-none border border-white/10 bg-[#17181b]/98 p-0',
}

export function MobileDrawer({
  open,
  onOpenChange,
  title,
  description,
  children,
  side = 'right',
}: MobileDrawerProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton
        className={cn(
          'zyc-modal-enter overflow-hidden border-white/10 text-zinc-50 shadow-2xl',
          SIDE_CLASS_NAMES[side]
        )}
      >
        <div className="border-b border-white/10 px-5 py-4">
          <DialogTitle className="text-base font-semibold">{title}</DialogTitle>
          {description ? (
            <DialogDescription className="mt-1 text-sm text-white/60">
              {description}
            </DialogDescription>
          ) : null}
        </div>
        <div className="zyc-scrollbar max-h-[calc(100vh-7rem)] overflow-y-auto px-5 py-5">
          {children}
        </div>
      </DialogContent>
    </Dialog>
  )
}
