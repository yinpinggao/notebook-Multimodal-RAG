'use client'

export function CodeSnippetBlock({
  title,
  code,
}: {
  title: string
  code: string
}) {
  return (
    <div className="overflow-hidden rounded-[20px] border border-white/8 bg-black/26">
      <div className="border-b border-white/8 px-4 py-3 text-xs uppercase tracking-[0.16em] text-white/42">
        {title}
      </div>
      <pre className="overflow-x-auto px-4 py-4 text-xs leading-6 text-white/72">
        <code>{code}</code>
      </pre>
    </div>
  )
}
