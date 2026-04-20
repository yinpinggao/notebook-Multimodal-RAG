'use client'

export function DecayCurve({ values }: { values: number[] }) {
  const points = values
    .map((value, index) => `${index * 22},${48 - value / 2.3}`)
    .join(' ')

  return (
    <svg viewBox="0 0 100 52" className="h-16 w-full">
      <polyline
        fill="none"
        stroke="rgba(159, 113, 255, 0.95)"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  )
}
