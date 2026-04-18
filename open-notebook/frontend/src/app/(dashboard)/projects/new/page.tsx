'use client'

import Link from 'next/link'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle } from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import { useCreateDemoProject } from '@/lib/hooks/use-projects'
import { formatApiError } from '@/lib/utils/error-handler'

export default function NewProjectPage() {
  const router = useRouter()
  const { openNotebookDialog } = useCreateDialogs()
  const createDemoProject = useCreateDemoProject()

  useEffect(() => {
    openNotebookDialog()
  }, [openNotebookDialog])

  const handleCreateOrOpenDemo = async () => {
    try {
      const project = await createDemoProject.mutateAsync()
      router.push(`/projects/${encodeURIComponent(project.id)}/overview`)
    } catch {}
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6">
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>新建项目</CardTitle>
              <CardDescription>
                第一阶段继续复用现有 notebook 创建流程。也可以直接打开预置 Demo 项目，跳过手动建空项目。
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Button onClick={openNotebookDialog}>再次打开创建对话框</Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    void handleCreateOrOpenDemo()
                  }}
                  disabled={createDemoProject.isPending}
                >
                  {createDemoProject.isPending ? '正在准备 Demo...' : '创建 / 打开 Demo 项目'}
                </Button>
                <Button asChild variant="outline">
                  <Link href="/projects">返回项目列表</Link>
                </Button>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button asChild variant="outline">
                  <Link href="/admin/evals">评测中心</Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/admin/jobs">任务队列</Link>
                </Button>
              </div>

              {createDemoProject.error ? (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Demo 项目暂时不可用</AlertTitle>
                  <AlertDescription>{formatApiError(createDemoProject.error)}</AlertDescription>
                </Alert>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}
