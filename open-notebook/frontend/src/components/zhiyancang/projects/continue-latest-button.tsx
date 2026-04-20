'use client'

import Link from 'next/link'
import { faArrowRight } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Button } from '@/components/ui/button'
import { buildProjectPath } from '@/lib/project-paths'

export function ContinueLatestButton({ projectId }: { projectId: string | null }) {
  if (!projectId) {
    return null
  }

  return (
    <Button
      asChild
      className="zyc-touch zyc-ripple rounded-full bg-white px-5 text-zinc-950 hover:bg-white/92"
    >
      <Link href={buildProjectPath({ projectId, section: 'overview' })}>
        Continue Latest Projects
        <FontAwesomeIcon icon={faArrowRight} className="ml-2 text-sm" />
      </Link>
    </Button>
  )
}
