'use client'

import { useMemo } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  Bot,
  ChevronDown,
  Command,
  FolderKanban,
  LayoutPanelLeft,
  LogOut,
  Sparkles,
  UserCircle2,
} from 'lucide-react'

import { LanguageToggle } from '@/components/common/LanguageToggle'
import { ThemeToggle } from '@/components/common/ThemeToggle'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AssistantView,
  HarnessAgentId,
  mergeAssistantSearchParams,
} from '@/lib/assistant-workspace'
import { useAuth } from '@/lib/hooks/use-auth'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useAssistantWorkspaceStore } from '@/lib/stores/assistant-workspace-store'
import { ProjectSummaryResponse } from '@/lib/types/api'
import { cn } from '@/lib/utils'

interface AssistantTopBarProps {
  projects: ProjectSummaryResponse[]
  isLoading?: boolean
}

export function AssistantTopBar({
  projects,
  isLoading = false,
}: AssistantTopBarProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { logout } = useAuth()
  const { t } = useTranslation()
  const { currentAgent, currentProjectId, currentView } = useAssistantWorkspaceStore()

  const agentOptions = useMemo(
    () => [
      {
        id: 'research' as HarnessAgentId,
        label: t.assistant.researchAgent,
      },
      {
        id: 'retrieval' as HarnessAgentId,
        label: t.assistant.retrievalAgent,
      },
      {
        id: 'visual' as HarnessAgentId,
        label: t.assistant.visualAgent,
      },
      {
        id: 'synthesis' as HarnessAgentId,
        label: t.assistant.synthesisAgent,
      },
    ],
    [t]
  )

  const viewOptions = useMemo(
    () => [
      {
        id: 'knowledge' as AssistantView,
        label: t.assistant.knowledgeHub,
      },
      {
        id: 'workspace' as AssistantView,
        label: t.assistant.workspace,
      },
      {
        id: 'memory' as AssistantView,
        label: t.assistant.memoryManager,
      },
    ],
    [t]
  )

  const handleProjectChange = (projectId: string) => {
    router.replace(
      mergeAssistantSearchParams(searchParams, {
        projectId,
        threadId: null,
      }),
      { scroll: false }
    )
  }

  const handleAgentChange = (agent: HarnessAgentId) => {
    router.replace(
      mergeAssistantSearchParams(searchParams, {
        agent,
      }),
      { scroll: false }
    )
  }

  const handleViewChange = (view: AssistantView) => {
    router.replace(
      mergeAssistantSearchParams(searchParams, {
        view,
      }),
      { scroll: false }
    )
  }

  const handleOpenCommandPalette = () => {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('command-palette:toggle'))
    }
  }

  return (
    <header className="border-b border-border/70 bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={handleOpenCommandPalette}
          >
            <Command className="h-4 w-4" />
            {t.common.quickActions}
          </Button>

          <div className="hidden items-center gap-1 rounded-md border border-border/70 bg-muted/30 p-1 md:flex">
            {viewOptions.map((option) => (
              <Button
                key={option.id}
                type="button"
                size="sm"
                variant={currentView === option.id ? 'secondary' : 'ghost'}
                className={cn('h-8 px-3', currentView === option.id && 'shadow-none')}
                onClick={() => handleViewChange(option.id)}
              >
                {option.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={currentProjectId}
            onValueChange={handleProjectChange}
            disabled={isLoading || projects.length === 0}
          >
            <SelectTrigger className="min-w-[220px]">
              <FolderKanban className="mr-2 h-4 w-4 text-muted-foreground" />
              <SelectValue placeholder={t.assistant.selectProject} />
            </SelectTrigger>
            <SelectContent>
              {projects.map((project) => (
                <SelectItem key={project.id} value={project.id}>
                  {project.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {currentView === 'workspace' ? (
            <Select
              value={currentAgent}
              onValueChange={(value) => handleAgentChange(value as HarnessAgentId)}
            >
              <SelectTrigger className="min-w-[200px]">
                <Bot className="mr-2 h-4 w-4 text-muted-foreground" />
                <SelectValue placeholder={t.assistant.selectAgent} />
              </SelectTrigger>
              <SelectContent>
                {agentOptions.map((option) => (
                  <SelectItem key={option.id} value={option.id}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null}

          <div className="hidden items-center gap-2 md:flex">
            <ThemeToggle iconOnly />
            <LanguageToggle iconOnly />
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button type="button" variant="outline" size="sm" className="gap-2">
                <UserCircle2 className="h-4 w-4" />
                <span className="hidden sm:inline">{t.common.appName}</span>
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="px-3 py-2 text-xs text-muted-foreground">
                <div className="flex items-center gap-2 font-medium text-foreground">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  {t.assistant.workspace}
                </div>
                <div className="mt-1 leading-5">
                  {t.assistant.singleWorkspaceHint}
                </div>
              </div>
              <DropdownMenuItem onSelect={logout} className="gap-2">
                <LogOut className="h-4 w-4" />
                {t.common.signOut}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2 md:hidden">
        <LayoutPanelLeft className="h-4 w-4 text-muted-foreground" />
        <div className="flex flex-wrap gap-2">
          {viewOptions.map((option) => (
            <Button
              key={option.id}
              type="button"
              size="sm"
              variant={currentView === option.id ? 'secondary' : 'outline'}
              onClick={() => handleViewChange(option.id)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>
    </header>
  )
}
