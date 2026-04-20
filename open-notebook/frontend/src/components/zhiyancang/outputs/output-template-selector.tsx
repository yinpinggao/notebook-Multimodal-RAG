'use client'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useZycUIStore } from '@/lib/stores/zyc-ui-store'

const DEFAULT_TEMPLATE_OPTIONS = [
  'Project Summary',
  'Defense Pitch',
  'Poster Copy',
  'PPT Outline',
  'Competition Brief',
]

export function OutputTemplateSelector({ templates = DEFAULT_TEMPLATE_OPTIONS }: { templates?: string[] }) {
  const { selectedOutputTemplate, setSelectedOutputTemplate } = useZycUIStore()
  const options = templates.length > 0 ? templates : DEFAULT_TEMPLATE_OPTIONS

  return (
    <div className="zyc-panel rounded-[24px] px-5 py-5 shadow-zyc-soft">
      <div className="text-sm font-medium text-white">Template Selector</div>
      <Select value={selectedOutputTemplate} onValueChange={setSelectedOutputTemplate}>
        <SelectTrigger className="mt-4 h-12 rounded-[20px] border-white/10 bg-white/6 text-white">
          <SelectValue placeholder="Choose a template" />
        </SelectTrigger>
        <SelectContent className="rounded-[20px] border-white/10 bg-[#18191d]/96 text-white">
          {options.map((template) => (
            <SelectItem key={template} value={template}>
              {template}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
