'use client'

import type { ZycRunModel } from '@/lib/zhiyancang/types'

export function RunLogHeader({ run }: { run: ZycRunModel }) {
  return (
    <div className="zyc-glass rounded-[24px] px-5 py-5">
      <div className="grid gap-4 lg:grid-cols-4">
        <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
          <div className="text-xs uppercase tracking-[0.16em] text-white/38">Run Goal</div>
          <div className="mt-3 text-sm leading-7 text-white">{run.goal}</div>
        </div>
        <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
          <div className="text-xs uppercase tracking-[0.16em] text-white/38">Agent Used</div>
          <div className="mt-3 text-sm text-white">{run.agentUsed}</div>
        </div>
        <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
          <div className="text-xs uppercase tracking-[0.16em] text-white/38">Evidence</div>
          <div className="mt-3 text-sm text-white">{run.evidenceReferenced.length}</div>
        </div>
        <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
          <div className="text-xs uppercase tracking-[0.16em] text-white/38">Tools</div>
          <div className="mt-3 text-sm text-white">{run.toolsInvoked.length}</div>
        </div>
      </div>
    </div>
  )
}
