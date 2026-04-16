'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { BookOpen } from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useNotebooks } from '@/lib/hooks/use-notebooks'

export default function VRAGCompatibilityPage() {
  const { t } = useTranslation()
  const router = useRouter()
  const searchParams = useSearchParams()
  const notebookId = searchParams.get('id')
  const { data: notebooks = [], isLoading } = useNotebooks()

  useEffect(() => {
    if (notebookId) {
      router.replace(`/notebooks/${encodeURIComponent(notebookId)}/visual`)
    }
  }, [notebookId, router])

  if (isLoading || notebookId) {
    return (
      <AppShell>
        <div className="flex flex-col flex-1 items-center justify-center p-6">
          <LoadingSpinner size="lg" />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="flex flex-col flex-1 items-center justify-center p-6">
        <BookOpen className="h-16 w-16 text-muted-foreground mb-4" />
        <h1 className="text-2xl font-bold mb-2">{t.vrag?.title || 'Visual RAG'}</h1>
        <p className="text-muted-foreground text-center max-w-md mb-6">
          {t.vrag?.selectNotebook || 'Please select a notebook to use Visual RAG'}
        </p>
        <Select
          onValueChange={(value) => {
            if (value) {
              router.push(`/notebooks/${encodeURIComponent(value)}/visual`)
            }
          }}
        >
          <SelectTrigger className="w-[300px]">
            <SelectValue placeholder={t.vrag?.selectNotebook || 'Select a notebook...'} />
          </SelectTrigger>
          <SelectContent>
            {notebooks.map((notebook) => (
              <SelectItem key={notebook.id} value={notebook.id}>
                {notebook.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </AppShell>
  )
}
