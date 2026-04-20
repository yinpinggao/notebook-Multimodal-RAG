import type { ReactNode } from 'react'

import { ZycShell } from '@/components/zhiyancang/layout/zyc-shell'

export default function ZhiyancangLayout({ children }: { children: ReactNode }) {
  return <ZycShell>{children}</ZycShell>
}
