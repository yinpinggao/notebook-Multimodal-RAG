import { AssistantLayoutShell } from '@/components/harness/AssistantLayoutShell'
import { AppShell } from '@/components/layout/AppShell'

export default function AssistantLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AppShell>
      <AssistantLayoutShell>{children}</AssistantLayoutShell>
    </AppShell>
  )
}
