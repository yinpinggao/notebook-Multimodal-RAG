'use client'

import { useCallback, useEffect, useId, useMemo, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import {
  Bot,
  Boxes,
  Command as CommandIcon,
  FileSearch,
  FileText,
  FlaskConical,
  FolderKanban,
  Monitor,
  Moon,
  Plus,
  Settings,
  Sun,
} from 'lucide-react'

import {
  CommandDialog,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { useCreateDialogs } from '@/lib/hooks/use-create-dialogs'
import { useProjectMemory } from '@/lib/hooks/use-project-memory'
import { useProjects } from '@/lib/hooks/use-projects'
import { projectIdToNotebookId } from '@/lib/project-alias'
import { useTranslation } from '@/lib/hooks/use-translation'
import { buildProjectPath } from '@/lib/project-paths'
import { useTheme } from '@/lib/stores/theme-store'

const COMMAND_TOGGLE_EVENT = 'command-palette:toggle'

function resolveProjectIdFromPath(pathname: string | null) {
  if (!pathname?.startsWith('/projects/')) {
    return ''
  }

  const [, , projectId] = pathname.split('/')
  return projectId ? projectIdToNotebookId(projectId) : ''
}

export function CommandPalette() {
  const commandInputId = useId()
  const router = useRouter()
  const pathname = usePathname()
  const { t } = useTranslation()
  const { openSourceDialog, openNotebookDialog } = useCreateDialogs()
  const { setTheme } = useTheme()
  const { data: projects = [] } = useProjects(false)

  const currentProjectId = useMemo(() => resolveProjectIdFromPath(pathname), [pathname])
  const { data: memories = [] } = useProjectMemory(currentProjectId)

  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')

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
      description="搜索项目、资料、后台入口和主题设置。"
      className="sm:max-w-2xl"
    >
      <CommandInput
        id={commandInputId}
        value={query}
        onValueChange={setQuery}
        placeholder="搜索项目、页面和动作..."
        aria-label={t.common.quickActions}
      />
      <CommandList>
        <CommandGroup heading="导航">
          <CommandItem onSelect={() => handleNavigate('/projects')}>
            <FolderKanban className="h-4 w-4" />
            <span>{t.navigation.projects}</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate('/models')}>
            <Bot className="h-4 w-4" />
            <span>{t.navigation.models}</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate('/settings')}>
            <Settings className="h-4 w-4" />
            <span>{t.navigation.settings}</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate('/admin/evals')}>
            <FlaskConical className="h-4 w-4" />
            <span>评测中心</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate('/admin/jobs')}>
            <Boxes className="h-4 w-4" />
            <span>任务队列</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate('/assistant')}>
            <CommandIcon className="h-4 w-4" />
            <span>旧工作台</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate('/sources')}>
            <FileText className="h-4 w-4" />
            <span>资料列表</span>
          </CommandItem>
          <CommandItem onSelect={() => handleNavigate('/vrag')}>
            <FileSearch className="h-4 w-4" />
            <span>视觉证据</span>
          </CommandItem>
        </CommandGroup>

        <CommandGroup heading={t.assistant.projectsHeading}>
          {projects.map((project) => (
            <CommandItem
              key={project.id}
              value={`project ${project.name} ${project.description || ''}`}
              onSelect={() =>
                handleNavigate(buildProjectPath({ projectId: project.id, section: 'overview' }))
              }
            >
              <FolderKanban className="h-4 w-4" />
              <span>{project.name}</span>
            </CommandItem>
          ))}
        </CommandGroup>

        {currentProjectId ? (
          <CommandGroup heading="当前项目记忆">
            {memories.slice(0, 8).map((memory) => (
              <CommandItem
                key={memory.id}
                value={`memory ${memory.text} ${memory.type} ${memory.status}`}
                onSelect={() =>
                  handleNavigate(buildProjectPath({ projectId: currentProjectId, section: 'memory' }))
                }
              >
                <Boxes className="h-4 w-4" />
                <span>{memory.text}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        ) : null}

        <CommandGroup heading={t.navigation.create}>
          <CommandItem onSelect={() => handleSelect(() => openNotebookDialog())}>
            <Plus className="h-4 w-4" />
            <span>新建项目</span>
          </CommandItem>
          <CommandItem onSelect={() => handleSelect(() => openSourceDialog())}>
            <Plus className="h-4 w-4" />
            <span>导入资料</span>
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
      </CommandList>
    </CommandDialog>
  )
}
