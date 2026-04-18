'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { projectIdToNotebookId } from '@/lib/project-alias'

export default function ProjectEvidencePage() {
  const params = useParams()
  const projectId = params?.projectId ? String(params.projectId) : ''
  const notebookId = projectIdToNotebookId(projectId)

  return (
    <Card>
      <CardHeader>
        <CardTitle>证据工作台</CardTitle>
        <CardDescription>
          这一页先占住统一 Evidence QA 的入口。真实的 ask 服务和线程体验会在后续 issue 中接入。
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button asChild>
          <Link href={`/notebooks/${encodeURIComponent(notebookId)}`}>打开旧版 Notebook Chat</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href={`/notebooks/${encodeURIComponent(notebookId)}/visual`}>打开 Visual RAG</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/search">打开 Ask / Search</Link>
        </Button>
      </CardContent>
    </Card>
  )
}
