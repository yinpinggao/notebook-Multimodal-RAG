'use client'

import { useCallback, useEffect, useId, useMemo, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import {
  Bot,
  BrainCircuit,
  Command as CommandIcon,
  FolderKanban,
  LayoutDashboard,
  LayoutPanelLeft,
  Plus,
  Settings,
  Sparkles,
  Sun,
  Moon,
  Monitor,
} from 'lucide-react'

import {
  CommandDialog,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  buildAssistantUrl,
  HarnessAgentId,
  mergeAssistantSearchParams,
} from '@/lib/assistant-workspace'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import { useProjectMemory } from '@/lib/hooks/use-project-memory'
import { useProjects } from '@/lib/hooks/use-projects'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useTheme } from '@/lib/stores/theme-store'

const COMMAND_TOGGLE_EVENT = 'command-palette:toggle'

export function CommandPalette() {
  const commandInputId = useId()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { t } = useTranslation()
  const { openSourceDialog, openNotebookDialog } = useCreateDialogs()
  const { setTheme } = useTheme()
  const { data: projects = [] } = useProjects(false)
  const currentProjectId = searchParams.get('project') || ''
  const { data: memories = [] } = useProjectMemory(currentProjectId)

  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')

  const agentItems = useMemo(
    () => [
      { id: 'research' as HarnessAgentId, label: t.assistant.researchAgent },
      { id: 'retrieval' as HarnessAgentId, label: t.assistant.retrievalAgent },
      { id: 'visual' as HarnessAgentId, label: t.assistant.visualAgent },
      { id: 'synthesis' as HarnessAgentId, label: t.assistant.synthesisAgent },
    ],
    [t]
  )

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (
        target &&
        (target.isContentEditable ||
          ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
      ) {
        return
      }

      if (event.key === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        setOpen((value) => !value)
      }
    }

    const onToggle = () => {
      setOpen((value) => !value)
    }

    document.addEventListener('keydown', onKeyDown, true)
    window.addEventListener(COMMAND_TOGGLE_EVENT, onToggle)

    return () => {
      document.removeEventListener('keydown', onKeyDown, true)
      window.removeEventListener(COMMAND_TOGGLE_EVENT, onToggle)
    }
  }, [])

  useEffect(() => {
    if (!open) {
      setQuery('')
    }
  }, [open])

  const handleSelect = useCallback((callback: () => void) => {
    setOpen(false)
    setQuery('')
    setTimeout(callback, 0)
  }, [])

  const handleNavigate = useCallback(
    (href: string) => {
      handleSelect(() => router.push(href))
    },
    [handleSelect, router]
  )

  return (
    <CommandDialog
      open={open}
      onOpenChange={setOpen}
      title={t.common.quickActions}
      description={t.assistant.commandPaletteHint}
      className="sm:max-w-2xl"
    >
      <CommandInput
        id={commandInputId}
        value={query}
        onValueChange={setQuery}
        placeholder={t.assistant.commandPalettePlaceholder}
        aria-label={t.common.quickActions}
      />
      <CommandList>
        <CommandGroup heading={t.navigation.nav}>
          <CommandItem onSelect={() => handleNavigate('/dashboard')}>
            <LayoutDashboard className="h-4 w-4" />
            <span>{t.navigation.dashboard}</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate(buildAssistantUrl({ view: 'knowledge' }))}>
            <FolderKanban className="h-4 w-4" />
            <span>{t.assistant.knowledgeHub}</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate(buildAssistantUrl({ view: 'workspace' }))}>
            <LayoutPanelLeft className="h-4 w-4" />
            <span>{t.assistant.workspace}</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate(buildAssistantUrl({ view: 'memory' }))}>
            <BrainCircuit className="h-4 w-4" />
            <span>{t.assistant.memoryManager}</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate('/models')}>
            <Bot className="h-4 w-4" />
            <span>{t.navigation.models}</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate('/settings')}>
            <Settings className="h-4 w-4" />
            <span>{t.navigation.settings}</span>
          </CommandItem>
        </CommandGroup>

        <CommandGroup heading={t.assistant.projectsHeading}>
          {projects.map((project) => (
            <CommandItem
              key={project.id}
              value={`project ${project.name} ${project.description || ''}`}
              onSelect={() =>
                handleNavigate(buildAssistantUrl({ projectId: project.id, view: 'knowledge' }))
              }
            >
              <FolderKanban className="h-4 w-4" />
              <span>{project.name}</span>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandGroup heading={t.assistant.agents}>
          {agentItems.map((item) => (
            <CommandItem
              key={item.id}
              value={`agent ${item.label}`}
              onSelect={() =>
                handleNavigate(
                  pathname === '/assistant'
                    ? mergeAssistantSearchParams(searchParams, { agent: item.id })
                    : buildAssistantUrl({ agent: item.id })
                )
              }
            >
              <Bot className="h-4 w-4" />
              <span>{item.label}</span>
            </CommandItem>
          ))}
        </CommandGroup>

        {currentProjectId ? (
          <CommandGroup heading={t.assistant.currentMemoryHeading}>
            {memories.slice(0, 8).map((memory) => (
              <CommandItem
                key={memory.id}
                value={`memory ${memory.text} ${memory.type} ${memory.status}`}
                onSelect={() =>
                  handleNavigate(
                    mergeAssistantSearchParams(searchParams, {
                      view: 'memory',
                    })
                  )
                }
              >
                <BrainCircuit className="h-4 w-4" />
                <span>{memory.text}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        ) : null}

        <CommandGroup heading={t.navigation.create}>
          <CommandItem onSelect={() => handleSelect(() => openSourceDialog())}>
            <Plus className="h-4 w-4" />
            <span>{t.common.newSource}</span>
          </CommandItem>
          <CommandItem onSelect={() => handleSelect(() => openNotebookDialog())}>
            <Plus className="h-4 w-4" />
            <span>{t.assistant.createProject}</span>
          </CommandItem>
        </CommandGroup>

        <CommandGroup heading={t.navigation.theme}>
          <CommandItem onSelect={() => handleSelect(() => setTheme('light'))}>
            <Sun className="h-4 w-4" />
            <span>{t.common.light}</span>
          </CommandItem>
          <CommandItem onSelect={() => handleSelect(() => setTheme('dark'))}>
            <Moon className="h-4 w-4" />
            <span>{t.common.dark}</span>
          </CommandItem>
          <CommandItem onSelect={() => handleSelect(() => setTheme('system'))}>
            <Monitor className="h-4 w-4" />
            <span>{t.common.system}</span>
          </CommandItem>
        </CommandGroup>

        <CommandGroup heading={t.assistant.shortcutsHeading}>
          <CommandItem
            onSelect={() => handleNavigate(buildAssistantUrl({ view: 'workspace' }))}
          >
            <CommandIcon className="h-4 w-4" />
            <span>{t.common.quickActions}</span>
          </CommandItem>
          <CommandItem
            onSelect={() => handleNavigate(buildAssistantUrl({ view: 'workspace' }))}
          >
            <Sparkles className="h-4 w-4" />
            <span>{t.assistant.singleWorkspaceHint}</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
