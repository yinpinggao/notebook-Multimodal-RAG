'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { faArrowLeft, faFolderPlus } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useCreateProject } from '@/lib/hooks/use-projects'
import { buildProjectPath } from '@/lib/project-paths'
import { formatApiError } from '@/lib/utils/error-handler'

export default function NewProjectPage() {
  const router = useRouter()
  const createProject = useCreateProject()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!name.trim()) {
      return
    }

    try {
      const project = await createProject.mutateAsync({
        name: name.trim(),
        description: description.trim(),
      })
      router.push(buildProjectPath({ projectId: project.id, section: 'overview' }))
    } catch {
      // Inline error state handles this.
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <section className="zyc-glass rounded-[28px] px-6 py-8 shadow-zyc-soft">
        <div className="text-xs uppercase tracking-[0.16em] text-white/40">Projects / New</div>
        <h1 className="mt-3 text-3xl font-semibold text-white">Create a Research Track</h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-white/60">
          Start with a goal. Evidence, compare, memory, outputs, and runs will attach to this
          project space after creation.
        </p>
      </section>

      <form
        onSubmit={handleSubmit}
        className="zyc-panel rounded-[28px] border border-white/8 px-6 py-6 shadow-zyc-soft"
      >
        <div className="grid gap-5">
          <label className="grid gap-2">
            <span className="text-sm font-medium text-white">Project Name</span>
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="ZhiyanCang demo, grant brief, paper review..."
              className="h-12 rounded-[18px] border-white/10 bg-white/6 text-white placeholder:text-white/30"
            />
          </label>

          <label className="grid gap-2">
            <span className="text-sm font-medium text-white">Goal / Brief</span>
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe the research goal, the core question, or the deliverable."
              className="min-h-40 rounded-[18px] border-white/10 bg-white/6 text-white placeholder:text-white/30"
            />
          </label>
        </div>

        {createProject.error ? (
          <Alert variant="destructive" className="mt-5">
            <AlertTitle>Create project failed</AlertTitle>
            <AlertDescription>{formatApiError(createProject.error)}</AlertDescription>
          </Alert>
        ) : null}

        <div className="mt-6 flex flex-wrap gap-3">
          <Button
            type="submit"
            disabled={createProject.isPending || !name.trim()}
            className="rounded-full bg-white text-zinc-950 hover:bg-white/92"
          >
            <FontAwesomeIcon icon={faFolderPlus} className="mr-2" />
            {createProject.isPending ? 'Creating...' : 'Create Project'}
          </Button>
          <Button
            asChild
            variant="outline"
            className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10 hover:text-white"
          >
            <Link href="/projects">
              <FontAwesomeIcon icon={faArrowLeft} className="mr-2" />
              Back to Projects
            </Link>
          </Button>
        </div>
      </form>
    </div>
  )
}
