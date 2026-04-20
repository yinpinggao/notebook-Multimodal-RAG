'use client'

import Image from 'next/image'
import Link from 'next/link'
import { faArrowRight } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useZycLibrary } from '@/lib/hooks/use-zyc-global'
import { formatApiError } from '@/lib/utils/error-handler'

export default function LibraryPage() {
  const { data, error, isLoading } = useZycLibrary()

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Library unavailable</AlertTitle>
        <AlertDescription>{formatApiError(error)}</AlertDescription>
      </Alert>
    )
  }

  if (isLoading || !data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="zyc-glass rounded-[28px] px-5 py-6 lg:px-7">
        <div className="text-xs uppercase tracking-[0.16em] text-white/40">Global Layer / Library</div>
        <h1 className="mt-3 text-3xl font-semibold text-white lg:text-5xl">
          Documents, web sources, images, audio, and visual evidence.
        </h1>
      </section>

      <section className="grid gap-5 xl:grid-cols-5">
        {data.categories.map((category) => (
          <Link
            key={category.id}
            href={category.href}
            className="zyc-hover-lift overflow-hidden rounded-[24px] border border-white/8 bg-[#17181b]/92 shadow-zyc-soft"
          >
            <div className="relative h-48">
              <Image
                src={category.image}
                alt={category.title}
                fill
                className="object-cover"
                sizes="(max-width: 1024px) 100vw, 20vw"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#121212] via-transparent to-transparent" />
              <div className="absolute inset-x-0 bottom-0 px-4 pb-4">
                <div className="text-lg font-semibold text-white">{category.title}</div>
                <div className="mt-1 text-xs text-white/52">{category.count} resources</div>
              </div>
            </div>
            <div className="px-4 py-4 text-sm leading-7 text-white/62">{category.description}</div>
          </Link>
        ))}
      </section>

      <section className="zyc-panel rounded-[28px] px-5 py-5 shadow-zyc-soft">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-medium text-white">Recent Resources</div>
            <p className="mt-1 text-sm text-white/52">
              Keep the latest material visible before it turns into project evidence.
            </p>
          </div>
          <Link href="/sources" className="text-sm text-white/68 hover:text-white">
            Open all
            <FontAwesomeIcon icon={faArrowRight} className="ml-2" />
          </Link>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          {data.recent.map((item) => (
            <div key={item.id} className="rounded-[22px] border border-white/8 bg-white/4 px-4 py-4">
              <div className="text-base font-medium text-white">{item.title}</div>
              <div className="mt-2 text-xs uppercase tracking-[0.16em] text-white/42">{item.type}</div>
              <div className="mt-3 text-sm text-white/60">{item.source}</div>
              <div className="mt-1 text-xs text-white/42">{item.updatedAt}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
