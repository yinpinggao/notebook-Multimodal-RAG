'use client'

import { BrainCircuit, Database, FileText, ImageIcon, Sparkles } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ProjectOverviewStats,
  ProjectWorkspaceSummary,
  formatProjectTimestamp,
} from '@/lib/project-workspace'

interface ProjectOverviewHeaderProps {
  project: ProjectWorkspaceSummary
  stats: ProjectOverviewStats
}

export function ProjectOverviewHeader({
  project,
  stats,
}: ProjectOverviewHeaderProps) {
  const noteCountLabel = stats.noteCount ?? '--'

  return (
    <Card className="border-border/70">
      <CardHeader className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">项目空间 / Project Workspace</Badge>
          <Badge variant={project.status === 'archived' ? 'secondary' : 'default'}>
            {project.status === 'archived' ? '已归档' : '进行中'}
          </Badge>
        </div>

        <div className="space-y-3">
          <div className="space-y-2">
            <CardTitle className="break-words text-3xl">{project.name}</CardTitle>
            <CardDescription className="max-w-3xl text-sm leading-6">
              {project.description || '先把资料组织成项目上下文，再进入证据问答、对比和输出。'}
            </CardDescription>
          </div>

          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span>创建于 {formatProjectTimestamp(project.createdAt)}</span>
            <span>最近整理 {formatProjectTimestamp(project.updatedAt)}</span>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-md border border-border/70 p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Database className="h-3.5 w-3.5" />
              资料总数
            </div>
            <div className="mt-2 text-2xl font-semibold">{project.sourceCount}</div>
          </div>

          <div className="rounded-md border border-border/70 p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              项目笔记
            </div>
            <div className="mt-2 text-2xl font-semibold">{noteCountLabel}</div>
          </div>

          <div className="rounded-md border border-border/70 p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5" />
              文本索引就绪
            </div>
            <div className="mt-2 text-2xl font-semibold">{stats.embeddedSourceCount}</div>
          </div>

          <div className="rounded-md border border-border/70 p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <ImageIcon className="h-3.5 w-3.5" />
              视觉索引就绪
            </div>
            <div className="mt-2 text-2xl font-semibold">{stats.visualReadyCount}</div>
          </div>

          <div className="rounded-md border border-border/70 p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <BrainCircuit className="h-3.5 w-3.5" />
              已沉淀洞察
            </div>
            <div className="mt-2 text-2xl font-semibold">{stats.insightCount}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
