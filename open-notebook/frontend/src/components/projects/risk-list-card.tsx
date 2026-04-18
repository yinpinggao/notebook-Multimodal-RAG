import { AlertTriangle } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface RiskListCardProps {
  items: string[]
}

export function RiskListCard({ items }: RiskListCardProps) {
  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle>风险与开放问题</CardTitle>
        <CardDescription>
          先把最值得盯住的缺口亮出来，避免在关键问题上失焦。
        </CardDescription>
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          {items.map((item, index) => (
            <div
              key={`${item}-${index}`}
              className="flex gap-3 rounded-md border border-border/70 p-3"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
              <p className="text-sm leading-6">{item}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
