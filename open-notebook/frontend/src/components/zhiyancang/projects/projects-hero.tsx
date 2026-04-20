'use client'

import { ContinueLatestButton } from '@/components/zhiyancang/projects/continue-latest-button'
import { useTranslation } from '@/lib/hooks/use-translation'

export function ProjectsHero({ latestProjectId }: { latestProjectId: string | null }) {
  const { t } = useTranslation()

  return (
    <section className="zyc-page-enter zyc-glass overflow-hidden rounded-[28px] px-5 py-6 lg:px-7 lg:py-8">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl space-y-3">
          <div className="text-xs uppercase tracking-[0.18em] text-white/48">
            {t.zhiyancang.projects}
          </div>
          <h1 className="max-w-4xl text-3xl font-semibold leading-tight text-white lg:text-5xl">
            ZhiyanCang
            <span className="block text-white/78">{t.zhiyancang.slogan}</span>
          </h1>
          <p className="max-w-2xl text-sm leading-7 text-white/62 lg:text-base">
            A minimalist operating surface for research teams that need evidence, memory,
            outputs, and runs to stay in one place.
          </p>
        </div>

        <ContinueLatestButton projectId={latestProjectId} />
      </div>
    </section>
  )
}
