'use client'

import { faBullseye, faCircleQuestion, faFlagCheckered } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

interface OverviewSummaryCardProps {
  title: string
  content: string
  icon?: 'goal' | 'questions' | 'conclusion'
}

const ICON_MAP = {
  goal: faBullseye,
  questions: faCircleQuestion,
  conclusion: faFlagCheckered,
}

export function OverviewSummaryCard({
  title,
  content,
  icon = 'goal',
}: OverviewSummaryCardProps) {
  return (
    <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
      <div className="flex items-center gap-3 text-sm font-medium text-white/78">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/8 text-white/70">
          <FontAwesomeIcon icon={ICON_MAP[icon]} />
        </div>
        {title}
      </div>
      <p className="mt-4 text-sm leading-7 text-white/68">{content}</p>
    </div>
  )
}
