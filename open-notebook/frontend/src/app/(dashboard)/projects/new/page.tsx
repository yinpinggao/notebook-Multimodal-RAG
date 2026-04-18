'use client'

import Link from 'next/link'
import { useEffect } from 'react'

import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'

export default function NewProjectPage() {
  const { openNotebookDialog } = useCreateDialogs()

  useEffect(() => {
    openNotebookDialog()
  }, [openNotebookDialog])

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6">
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>新建项目</CardTitle>
              <CardDescription>
                第一阶段复用现有 notebook 创建流程。完成创建后，项目会出现在新的 Projects 入口下。
              </CardDescription>
            </CardHeader>
            <CardContent className="flex gap-2">
              <Button onClick={openNotebookDialog}>再次打开创建对话框</Button>
              <Button asChild variant="outline">
                <Link href="/projects">返回项目列表</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}
