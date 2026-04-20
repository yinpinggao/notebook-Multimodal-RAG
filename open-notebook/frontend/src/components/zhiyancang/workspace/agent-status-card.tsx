'use client'

import {
  faBinoculars,
  faCameraRetro,
  faPenNib,
  faUserAstronaut,
} from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import type { ZycAgentCard } from '@/lib/zhiyancang/types'

const ICONS = {
  researcher: faUserAstronaut,
  retriever: faBinoculars,
  visual: faCameraRetro,
  synthesizer: faPenNib,
}

export function AgentStatusCard({ agent }: { agent: ZycAgentCard }) {
  return (
    <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/8 text-white/70">
            <FontAwesomeIcon icon={ICONS[agent.id]} />
          </div>
          <div>
            <div className="text-base font-semibold text-white">{agent.title}</div>
            <div className="mt-1 text-xs uppercase tracking-[0.16em] text-white/44">
              {agent.status}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 space-y-4">
        <div>
          <div className="text-xs uppercase tracking-[0.16em] text-white/38">Task Input</div>
          <p className="mt-2 text-sm leading-7 text-white/68">{agent.taskInput}</p>
        </div>

        <div>
          <div className="text-xs uppercase tracking-[0.16em] text-white/38">Plan</div>
          <div className="mt-2 space-y-2">
            {agent.plan.map((step, index) => (
              <div key={step} className="rounded-2xl border border-white/8 bg-white/4 px-4 py-3 text-sm text-white/64">
                {index + 1}. {step}
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="text-xs uppercase tracking-[0.16em] text-white/38">Result</div>
          <p className="mt-2 text-sm leading-7 text-white/68">{agent.result}</p>
        </div>
      </div>
    </div>
  )
}
