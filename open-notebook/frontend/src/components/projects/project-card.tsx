'use client'

import Link from 'next/link'
import { ArrowRight, FolderKanban, ScrollText, Sparkles, BrainCircuit } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ProjectWorkspaceSummary,
  formatProjectTimestamp,
} from '@/lib/project-workspace'

interface ProjectCardProps {
  project: ProjectWorkspaceSummary
  href: string
  eyebrow?: string
  ctaLabel?: string
}

export function ProjectCard({
  project,
  href,
  eyebrow = '项目空间',
  ctaLabel = '进入项目',
}: ProjectCardProps) {
  const noteCountLabel = project.noteCount ?? '--'

  return (
    <Card className="flex h-full flex-col justify-between border-border/70">
      <CardHeader className="space-y-4 pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">{eyebrow}</Badge>
          <Badge variant={project.status === 'archived' ? 'secondary' : 'default'}>
            {project.status === 'archived' ? '已归档' : '进行中'}
          </Badge>
        </div>

        <div className="space-y-2">
          <CardTitle className="break-words text-xl">{project.name}</CardTitle>
          <CardDescription className="line-clamp-3 min-h-[3.75rem] text-sm leading-6">
            {project.description || '从资料、证据到产物，都在这个项目空间里持续沉淀。'}
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="rounded-md border border-border/70 p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <FolderKanban className="h-3.5 w-3.5" />
              资料
            </div>
            <div className="mt-2 text-lg font-semibold">{project.sourceCount}</div>
          </div>

          <div className="rounded-md border border-border/70 p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <ScrollText className="h-3.5 w-3.5" />
              笔记
            </div>
            <div className="mt-2 text-lg font-semibold">{noteCountLabel}</div>
          </div>

          <div className="rounded-md border border-border/70 p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5" />
              产物
            </div>
            <div className="mt-2 text-lg font-semibold">{project.artifactCount}</div>
          </div>

          <div className="rounded-md border border-border/70 p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <BrainCircuit className="h-3.5 w-3.5" />
              记忆
            </div>
            <div className="mt-2 text-lg font-semibold">{project.memoryCount}</div>
          </div>
        </div>

        <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
          <div className="space-y-1">
            <div>创建于 {formatProjectTimestamp(project.createdAt)}</div>
            <div>最近整理 {formatProjectTimestamp(project.updatedAt)}</div>
          </div>

          <Button asChild size="sm">
            <Link href={href}>
              {ctaLabel}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
