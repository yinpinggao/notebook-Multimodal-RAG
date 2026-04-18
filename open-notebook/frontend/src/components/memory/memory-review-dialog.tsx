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
import { MemoryRecordResponse, MemoryStatus } from '@/lib/types/api'

interface MemoryReviewDialogProps {
  memory: MemoryRecordResponse | null
  open: boolean
  isSaving?: boolean
  isDeleting?: boolean
  onOpenChange: (open: boolean) => void
  onSave: (payload: { text: string; status: MemoryStatus }) => void
  onDelete: () => void
}

export function MemoryReviewDialog({
  memory,
  open,
  isSaving = false,
  isDeleting = false,
  onOpenChange,
  onSave,
  onDelete,
}: MemoryReviewDialogProps) {
  const [text, setText] = useState('')
  const [status, setStatus] = useState<MemoryStatus>('draft')

  useEffect(() => {
    if (!memory) {
      setText('')
      setStatus('draft')
      return
    }

    setText(memory.text)
    setStatus(memory.status)
  }, [memory])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>审核记忆</DialogTitle>
          <DialogDescription>
            可以在这里改文字、改状态。确认后它才会进入长期记忆的稳定层。
          </DialogDescription>
        </DialogHeader>

        {memory ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="memory-text">记忆内容</Label>
              <Textarea
                id="memory-text"
                value={text}
                onChange={(event) => setText(event.target.value)}
                className="min-h-32"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="memory-status">状态</Label>
              <Select
                value={status}
                onValueChange={(value) => setStatus(value as MemoryStatus)}
              >
                <SelectTrigger id="memory-status" className="w-full">
                  <SelectValue placeholder="选择状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">draft</SelectItem>
                  <SelectItem value="accepted">accepted</SelectItem>
                  <SelectItem value="frozen">frozen</SelectItem>
                  <SelectItem value="deprecated">deprecated</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-medium">来源引用</div>
              <div className="space-y-2">
                {memory.source_refs.map((ref) => (
                  <div
                    key={`${ref.source_id}:${ref.internal_ref}`}
                    className="rounded-md border border-border/70 px-3 py-3 text-xs leading-5 text-muted-foreground"
                  >
                    {ref.citation_text || ref.internal_ref}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}

        <DialogFooter className="justify-between sm:justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={onDelete}
            disabled={isSaving || isDeleting}
          >
            {isDeleting ? '删除中...' : '删除'}
          </Button>

          <div className="flex flex-wrap justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSaving || isDeleting}
            >
              取消
            </Button>
            <Button
              type="button"
              onClick={() => onSave({ text, status })}
              disabled={isSaving || isDeleting}
            >
              {isSaving ? '保存中...' : '保存'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
