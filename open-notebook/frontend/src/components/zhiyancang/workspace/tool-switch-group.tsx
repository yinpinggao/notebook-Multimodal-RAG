'use client'

import { faSliders } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Checkbox } from '@/components/ui/checkbox'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import type { ZycToolToggle } from '@/lib/zhiyancang/types'

export function ToolSwitchGroup({ toggles }: { toggles: ZycToolToggle[] }) {
  return (
    <div className="rounded-[22px] border border-white/8 bg-white/4 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-white">Tool Switches</div>
          <div className="mt-1 text-xs text-white/45">
            Keep the active tool surface narrow.
          </div>
        </div>

        <Popover>
          <PopoverTrigger asChild>
            <button
              type="button"
              className="zyc-touch zyc-ripple inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white/70 transition hover:bg-white/10"
            >
              <FontAwesomeIcon icon={faSliders} />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-72 rounded-[20px] border-white/10 bg-[#18191d]/96 text-white">
            <div className="text-sm font-medium">Tool Surface</div>
            <p className="mt-2 text-sm leading-6 text-white/60">
              Enable only the switches that should affect the next run.
            </p>
          </PopoverContent>
        </Popover>
      </div>

      <div className="mt-4 space-y-3">
        {toggles.map((toggle) => (
          <label
            key={toggle.id}
            className="flex items-start gap-3 rounded-2xl border border-white/8 bg-black/16 px-4 py-3"
          >
            <Checkbox checked={toggle.enabled} className="mt-1 border-white/20 bg-white/6" />
            <div>
              <div className="text-sm font-medium text-white">{toggle.label}</div>
              <div className="mt-1 text-xs leading-6 text-white/50">{toggle.description}</div>
            </div>
          </label>
        ))}
      </div>
    </div>
  )
}
