'use client'

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import type { ReactNode } from 'react'

export function RunCollapsiblePanel({
  sections,
}: {
  sections: Array<{ id: string; title: string; content: ReactNode }>
}) {
  return (
    <Accordion type="single" collapsible defaultValue={sections[0]?.id} className="rounded-[24px] border border-white/8 bg-[#17181b]/92 px-5 py-2 shadow-zyc-soft">
      {sections.map((section) => (
        <AccordionItem key={section.id} value={section.id} className="border-white/8">
          <AccordionTrigger className="text-left text-base font-medium text-white hover:no-underline">
            {section.title}
          </AccordionTrigger>
          <AccordionContent>{section.content}</AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  )
}
