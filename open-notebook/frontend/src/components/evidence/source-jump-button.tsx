'use client'

import { usePathname, useRouter } from 'next/navigation'
import { ExternalLink } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useModalManager } from '@/lib/hooks/use-modal-manager'
import { useNavigation } from '@/lib/hooks/use-navigation'
import { resolveEvidenceTarget } from '@/lib/project-evidence'

interface SourceJumpButtonProps {
  sourceId?: string | null
  internalRef?: string | null
  label?: string
}

export function SourceJumpButton({
  sourceId,
  internalRef,
  label = '打开来源',
}: SourceJumpButtonProps) {
  const router = useRouter()
  const pathname = usePathname()
  const navigation = useNavigation()
  const { openModal } = useModalManager()

  const target = resolveEvidenceTarget({
    sourceId,
    internalRef,
  })

  if (!target) {
    return null
  }

  const handleClick = () => {
    if (target.kind === 'source') {
      navigation.setReturnTo(pathname, '返回证据工作台')
      router.push(`/sources/${encodeURIComponent(target.id)}`)
      return
    }

    openModal(target.kind, target.id)
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="h-8 gap-1"
      onClick={handleClick}
    >
      <ExternalLink className="h-3.5 w-3.5" />
      {label}
    </Button>
  )
}
