'use client'

import Link from 'next/link'

import { AppShell } from '@/components/layout/AppShell'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { notebookToProjectSummary } from '@/lib/project-alias'

export default function ProjectsPage() {
  const { openNotebookDialog } = useCreateDialogs()
  const { data: notebooks = [], isLoading } = useNotebooks(false)
  const projects = notebooks.map(notebookToProjectSummary)

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
          <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="outline">Project Workspace</Badge>
                <Badge variant="secondary">Notebook Alias</Badge>
              </div>
              <div className="space-y-1">
                <h1 className="text-2xl font-semibold tracking-tight">项目</h1>
                <p className="text-sm text-muted-foreground">
                  当前阶段复用现有 notebook 数据模型，把产品主入口切换到 project 工作台。
                </p>
              </div>
            </div>

            <div className="flex gap-2">
              <Button onClick={openNotebookDialog}>新建项目</Button>
              <Button asChild variant="outline">
                <Link href="/projects/new">打开新建页</Link>
              </Button>
            </div>
          </header>

          {isLoading ? (
            <div className="flex min-h-64 items-center justify-center">
              <LoadingSpinner size="lg" />
            </div>
          ) : projects.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>还没有项目</CardTitle>
                <CardDescription>
                  这里会逐步替代原有 notebooks 首页。当前点击“新建项目”会复用现有 notebook 创建流程。
                </CardDescription>
              </CardHeader>
              <CardContent className="flex gap-2">
                <Button onClick={openNotebookDialog}>创建第一个项目</Button>
                <Button asChild variant="outline">
                  <Link href="/notebooks">查看旧版 Notebooks</Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {projects.map((project) => (
                <Link key={project.id} href={`/projects/${encodeURIComponent(project.id)}/overview`}>
                  <Card className="h-full transition-colors hover:border-primary/50">
                    <CardHeader className="space-y-3">
                      <div className="flex items-center justify-between gap-3">
                        <CardTitle className="text-lg">{project.name}</CardTitle>
                        {project.archived ? <Badge variant="secondary">Archived</Badge> : null}
                      </div>
                      <CardDescription>
                        {project.description || '暂无项目描述，后续会在总览页承载项目画像与关键问题。'}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm text-muted-foreground">
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="outline">{project.sourceCount} 份资料</Badge>
                        <Badge variant="outline">{project.noteCount} 条笔记</Badge>
                      </div>
                      <div>底层实体：{project.notebookId}</div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
