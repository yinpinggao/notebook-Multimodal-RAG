'use client'

import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { MemoryStatus, MemoryType, SourceReferenceResponse } from '@/lib/types/api'
import { useTranslation } from '@/lib/hooks/use-translation'

interface SaveMemoryDialogProps {
  open: boolean
  isSaving?: boolean
  defaultText: string
  defaultType?: MemoryType
  defaultStatus?: MemoryStatus
  sourceRefs?: SourceReferenceResponse[]
  onOpenChange: (open: boolean) => void
  onSave: (payload: {
    text: string
    type: MemoryType
    status: MemoryStatus
    sourceRefs: SourceReferenceResponse[]
  }) => void
}

export function SaveMemoryDialog({
  open,
  isSaving = false,
  defaultText,
  defaultType = 'fact',
  defaultStatus = 'draft',
  sourceRefs = [],
  onOpenChange,
  onSave,
}: SaveMemoryDialogProps) {
  const { t } = useTranslation()
  const [text, setText] = useState(defaultText)
  const [type, setType] = useState<MemoryType>(defaultType)
  const [status, setStatus] = useState<MemoryStatus>(defaultStatus)

  useEffect(() => {
    setText(defaultText)
    setType(defaultType)
    setStatus(defaultStatus)
  }, [defaultStatus, defaultText, defaultType, open])

  const handleSave = () => {
    onSave({
      text,
      type,
      status,
      sourceRefs,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t.assistant.saveToMemory}</DialogTitle>
          <DialogDescription>{t.assistant.saveToMemoryHint}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="assistant-memory-text">{t.assistant.memoryContent}</Label>
            <Textarea
              id="assistant-memory-text"
              value={text}
              onChange={(event) => setText(event.target.value)}
              className="min-h-32"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="assistant-memory-type">{t.common.type}</Label>
              <Select value={type} onValueChange={(value) => setType(value as MemoryType)}>
                <SelectTrigger id="assistant-memory-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fact">{t.assistant.memoryTypeFact}</SelectItem>
                  <SelectItem value="term">{t.assistant.memoryTypeTerm}</SelectItem>
                  <SelectItem value="decision">{t.assistant.memoryTypeDecision}</SelectItem>
                  <SelectItem value="risk">{t.assistant.memoryTypeRisk}</SelectItem>
                  <SelectItem value="preference">{t.assistant.memoryTypePreference}</SelectItem>
                  <SelectItem value="question">{t.assistant.memoryTypeQuestion}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="assistant-memory-status">{t.assistant.memoryStatus}</Label>
              <Select value={status} onValueChange={(value) => setStatus(value as MemoryStatus)}>
                <SelectTrigger id="assistant-memory-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">{t.assistant.memoryStatusDraft}</SelectItem>
                  <SelectItem value="accepted">{t.assistant.memoryStatusAccepted}</SelectItem>
                  <SelectItem value="frozen">{t.assistant.memoryStatusFrozen}</SelectItem>
                  <SelectItem value="deprecated">{t.assistant.memoryStatusDeprecated}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">{t.common.references}</div>
            {sourceRefs.length === 0 ? (
              <div className="rounded-md border border-dashed border-border/70 px-3 py-3 text-xs text-muted-foreground">
                {t.assistant.noMemoryRefs}
              </div>
            ) : (
              <div className="space-y-2">
                {sourceRefs.map((ref) => (
                  <div
                    key={`${ref.source_id}:${ref.internal_ref}`}
                    className="rounded-md border border-border/70 px-3 py-3 text-xs leading-5 text-muted-foreground"
                  >
                    {ref.citation_text || ref.internal_ref}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            {t.common.cancel}
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            disabled={isSaving || !text.trim()}
          >
            {isSaving ? t.common.saving : t.assistant.saveToMemory}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
