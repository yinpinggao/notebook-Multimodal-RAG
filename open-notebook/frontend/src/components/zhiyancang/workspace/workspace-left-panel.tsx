'use client'

import { faThumbtack, faListCheck } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import type { ZycWorkspaceModel } from '@/lib/zhiyancang/types'

import { ToolSwitchGroup } from './tool-switch-group'

export function WorkspaceLeftPanel({ workspace }: { workspace: ZycWorkspaceModel }) {
  const {
    workspaceMemoryScope,
    workspaceRetrievalMode,
    setWorkspaceMemoryScope,
    setWorkspaceRetrievalMode,
  } = useZycUIStore()

  return (
    <div className="space-y-4">
      <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
        <div className="flex items-center gap-3 text-sm font-medium text-white">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/8 text-white/70">
            <FontAwesomeIcon icon={faListCheck} />
          </div>
          Task List
        </div>
        <div className="mt-4 space-y-3">
          {workspace.tasks.map((task) => (
            <div key={task.id} className="rounded-2xl border border-white/8 bg-white/4 px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm text-white">{task.title}</div>
                <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-white/50">
                  {task.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
        <div className="text-sm font-medium text-white">Retrieval Mode</div>
        <div className="mt-3 grid gap-3">
          <Select value={workspaceRetrievalMode} onValueChange={(value) => setWorkspaceRetrievalMode(value as typeof workspaceRetrievalMode)}>
            <SelectTrigger className="h-11 rounded-2xl border-white/10 bg-white/6 text-white">
              <SelectValue placeholder="Choose a retrieval mode" />
            </SelectTrigger>
            <SelectContent className="rounded-2xl border-white/10 bg-[#18191d]/96 text-white">
              {workspace.retrievalModes.map((mode) => (
                <SelectItem key={mode} value={mode}>
                  {mode.toUpperCase()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={workspaceMemoryScope} onValueChange={setWorkspaceMemoryScope}>
            <SelectTrigger className="h-11 rounded-2xl border-white/10 bg-white/6 text-white">
              <SelectValue placeholder="Choose memory scope" />
            </SelectTrigger>
            <SelectContent className="rounded-2xl border-white/10 bg-[#18191d]/96 text-white">
              {workspace.memoryScopes.map((scope) => (
                <SelectItem key={scope} value={scope}>
                  {scope}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
        <div className="flex items-center gap-3 text-sm font-medium text-white">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/8 text-white/70">
            <FontAwesomeIcon icon={faThumbtack} />
          </div>
          Pinned Evidence
        </div>
        <div className="mt-4 space-y-3">
          {workspace.pinnedEvidence.map((item) => (
            <div key={item.id} className="rounded-2xl border border-white/8 bg-white/4 px-4 py-3">
              <div className="text-sm font-medium text-white">{item.title}</div>
              <div className="mt-1 text-xs text-white/45">{item.source}</div>
            </div>
          ))}
        </div>
      </div>

      <ToolSwitchGroup toggles={workspace.toolToggles} />
    </div>
  )
}
