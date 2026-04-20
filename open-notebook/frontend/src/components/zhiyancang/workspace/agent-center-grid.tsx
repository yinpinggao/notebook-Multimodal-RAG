'use client'

import type { ZycWorkspaceModel } from '@/lib/zhiyancang/types'

import { AgentStatusCard } from './agent-status-card'

export function AgentCenterGrid({ workspace }: { workspace: ZycWorkspaceModel }) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {workspace.agents.map((agent) => (
        <AgentStatusCard key={agent.id} agent={agent} />
      ))}
    </div>
  )
}
