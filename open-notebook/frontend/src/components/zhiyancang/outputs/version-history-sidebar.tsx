'use client'

import { faClockRotateLeft, faRotate } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Button } from '@/components/ui/button'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'
import type { ZycOutputItem } from '@/lib/zhiyancang/types'

export function VersionHistorySidebar({
  item,
  onRegenerate,
  isRegenerating = false,
}: {
  item: ZycOutputItem | null
  onRegenerate?: (artifactId: string) => void
  isRegenerating?: boolean
}) {
  const { selectedOutputVersionId, setSelectedOutputVersionId } = useZycUIStore()

  if (!item) {
    return (
      <div className="rounded-[24px] border border-white/8 bg-white/4 px-5 py-5 text-sm text-white/55">
        Select an output card to inspect versions.
      </div>
    )
  }

  return (
    <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
      <div className="flex items-center gap-3 text-sm font-medium text-white">
        <FontAwesomeIcon icon={faClockRotateLeft} className="text-white/52" />
        Version History
      </div>
      <div className="mt-4 space-y-3">
        {item.versions.map((version) => (
          <button
            key={version.id}
            type="button"
            onClick={() => setSelectedOutputVersionId(version.id)}
            className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
              selectedOutputVersionId === version.id
                ? 'border-[rgba(83,194,123,0.32)] bg-[rgba(83,194,123,0.12)] text-white'
                : 'border-white/8 bg-white/4 text-white/64 hover:border-white/14 hover:bg-white/8'
            }`}
          >
            <div className="text-sm font-medium">{version.label}</div>
            <div className="mt-1 text-xs text-white/45">
              {version.generatedAt} · {version.status}
            </div>
          </button>
        ))}
      </div>

      <Button
        type="button"
        disabled={isRegenerating}
        onClick={() => {
          const versionId = selectedOutputVersionId || item.versions[0]?.id
          if (versionId) {
            onRegenerate?.(versionId)
          }
        }}
        className="zyc-touch zyc-ripple mt-5 w-full rounded-2xl bg-white text-zinc-950 hover:bg-white/92"
      >
        <FontAwesomeIcon icon={faRotate} className="mr-2" />
        {isRegenerating ? 'Regenerating...' : 'Regenerate'}
      </Button>
    </div>
  )
}
