'use client'

import Link from 'next/link'

import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { RebuildEmbeddings } from './components/RebuildEmbeddings'
import { SystemInfo } from './components/SystemInfo'
import { useTranslation } from '@/lib/hooks/use-translation'

export default function AdvancedPage() {
  const { t } = useTranslation()
  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            <div>
              <h1 className="text-3xl font-bold">{t.advanced.title}</h1>
              <p className="text-muted-foreground mt-2">
                {t.advanced.desc}
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Card className="border-border/70">
                <CardHeader>
                  <CardTitle>评测中心</CardTitle>
                  <CardDescription>
                    运行 `run_project_eval`，检查证据忠实度、对比一致性和记忆溯源覆盖率。
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button asChild variant="outline">
                    <Link href="/admin/evals">打开评测中心</Link>
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-border/70">
                <CardHeader>
                  <CardTitle>任务队列</CardTitle>
                  <CardDescription>
                    查看后台命令状态，定位失败任务，并对可重试任务重新提交。
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button asChild variant="outline">
                    <Link href="/admin/jobs">打开任务队列</Link>
                  </Button>
                </CardContent>
              </Card>
            </div>

            <SystemInfo />
            <RebuildEmbeddings />
          </div>
        </div>
      </div>
    </AppShell>
  )
}
