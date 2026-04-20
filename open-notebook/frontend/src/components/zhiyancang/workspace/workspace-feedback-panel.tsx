'use client'

import { faBookmark, faPaperclip, faWaveSquare } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Button } from '@/components/ui/button'
import type { ZycWorkspaceModel } from '@/lib/zhiyancang/types'

export function WorkspaceFeedbackPanel({
  workspace,
  onSaveMemory,
  onSaveArtifact,
  isSaving = false,
}: {
  workspace: ZycWorkspaceModel
  onSaveMemory?: () => void
  onSaveArtifact?: () => void
  isSaving?: boolean
}) {
  return (
    <div className="space-y-4">
      <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
        <div className="text-sm font-medium text-white">Citations</div>
        <div className="mt-4 space-y-3">
          {workspace.citations.map((citation) => (
            <div key={citation.id} className="rounded-2xl border border-[rgba(71,182,255,0.25)] bg-[rgba(71,182,255,0.08)] px-4 py-3">
              <div className="text-sm font-medium text-white">{citation.label}</div>
              <div className="mt-1 text-xs text-white/50">
                {citation.source} · {citation.page}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
        <div className="flex items-center gap-3 text-sm font-medium text-white">
          <FontAwesomeIcon icon={faWaveSquare} className="text-white/52" />
          Run Trace
        </div>
        <div className="mt-4 space-y-3">
          {workspace.runTrace.map((item) => (
            <div key={item} className="rounded-2xl border border-white/8 bg-white/4 px-4 py-3 text-sm text-white/64">
              {item}
            </div>
          ))}
        </div>
      </div>

      <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
        <div className="flex items-center gap-3 text-sm font-medium text-white">
          <FontAwesomeIcon icon={faPaperclip} className="text-white/52" />
          Key Logs
        </div>
        <div className="mt-4 space-y-3">
          {workspace.keyLogs.map((log) => (
            <div key={log.id} className="rounded-2xl border border-white/8 bg-black/16 px-4 py-3">
              <div className="text-xs uppercase tracking-[0.16em] text-white/40">{log.time}</div>
              <div className="mt-2 text-sm leading-7 text-white/66">{log.text}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Button
          type="button"
          disabled={isSaving}
          onClick={onSaveMemory}
          className="zyc-touch zyc-ripple rounded-2xl bg-white text-zinc-950 hover:bg-white/92"
        >
          <FontAwesomeIcon icon={faBookmark} className="mr-2" />
          {isSaving ? 'Saving...' : 'Save as Memory'}
        </Button>
        <Button
          type="button"
          disabled={isSaving}
          onClick={onSaveArtifact}
          variant="outline"
          className="zyc-touch zyc-ripple rounded-2xl border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
        >
          {isSaving ? 'Saving...' : 'Save as Artifact'}
        </Button>
      </div>
    </div>
  )
}
