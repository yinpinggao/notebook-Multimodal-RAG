'use client'

import { useMemo } from 'react'
import { VRAGDAG, VRAGMemoryNode } from '@/lib/types/api'
import { useTranslation } from '@/lib/hooks/use-translation'

interface DAGViewerProps {
  dag: VRAGDAG
  className?: string
}

const NODE_COLORS: Record<string, string> = {
  search: 'bg-blue-100 dark:bg-blue-900 border-blue-400 dark:border-blue-600',
  bbox_crop: 'bg-purple-100 dark:bg-purple-900 border-purple-400 dark:border-purple-600',
  summarize: 'bg-amber-100 dark:bg-amber-900 border-amber-400 dark:border-amber-600',
  answer: 'bg-green-100 dark:bg-green-900 border-green-400 dark:border-green-600',
}

const NODE_ICONS: Record<string, string> = {
  search: '🔍',
  bbox_crop: '✂️',
  summarize: '📝',
  answer: '✅',
}

const NODE_LABELS: Record<string, string> = {
  search: 'Search',
  bbox_crop: 'Crop',
  summarize: 'Summarize',
  answer: 'Answer',
}

export function DAGViewer({ dag, className = '' }: DAGViewerProps) {
  const { t } = useTranslation()

  // Layout nodes in a simple grid/tree
  const layout = useMemo(() => {
    if (dag.nodes.length === 0) return null

    // Group nodes by type for layering
    const layers: Record<string, VRAGMemoryNode[]> = {
      search: [],
      bbox_crop: [],
      summarize: [],
      answer: [],
    }

    for (const node of dag.nodes) {
      const type = node.type || 'search'
      if (layers[type]) {
        layers[type].push(node)
      } else {
        layers.search.push(node)
      }
    }

    // Calculate node positions
    const layerGapX = 160
    const nodeGapY = 80
    const startX = 40
    const startY = 40

    const nodePositions: Record<string, { x: number; y: number; width: number; height: number }> = {}

    let layerIndex = 0
    for (const [type, nodes] of Object.entries(layers)) {
      if (nodes.length === 0) continue

      const layerX = startX + layerIndex * layerGapX
      const perNodeHeight = nodes.length * nodeGapY
      const layerStartY = startY + Math.max(0, (Object.values(layers).filter(n => n.length > 0).length * nodeGapY - perNodeHeight) / 2)

      nodes.forEach((node, idx) => {
        nodePositions[node.id] = {
          x: layerX,
          y: layerStartY + idx * nodeGapY,
          width: 140,
          height: 56,
        }
      })

      layerIndex++
    }

    return { nodePositions, layers }
  }, [dag.nodes])

  if (dag.nodes.length === 0) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center text-muted-foreground">
          <div className="text-3xl mb-2">🔗</div>
          <p className="text-xs">{t.vrag?.dagEmpty || 'DAG will appear here as the agent reasons'}</p>
        </div>
      </div>
    )
  }

  if (!layout) return null

  const { nodePositions, layers } = layout
  const totalWidth = Math.max(...Object.values(nodePositions).map(n => n.x + n.width), 400) + 80
  const totalHeight = Math.max(...Object.values(nodePositions).map(n => n.y + n.height), 200) + 80

  return (
    <div className={`overflow-auto ${className}`} style={{ minHeight: 200 }}>
      <svg
        width={totalWidth}
        height={totalHeight}
        className="min-w-full"
      >
        {/* Edges */}
        {dag.edges.map((edge, idx) => {
          const sourcePos = nodePositions[edge.source]
          const targetPos = nodePositions[edge.target]
          if (!sourcePos || !targetPos) return null

          const x1 = sourcePos.x + sourcePos.width / 2
          const y1 = sourcePos.y + sourcePos.height
          const x2 = targetPos.x + targetPos.width / 2
          const y2 = targetPos.y

          return (
            <g key={`edge-${idx}`}>
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="hsl(var(--muted-foreground))"
                strokeWidth={1.5}
                strokeOpacity={0.5}
              />
              <polygon
                points={`${x2},${y2} ${x2 - 4},${y2 - 8} ${x2 + 4},${y2 - 8}`}
                fill="hsl(var(--muted-foreground))"
                fillOpacity={0.5}
              />
            </g>
          )
        })}

        {/* Nodes */}
        {dag.nodes.map((node) => {
          const pos = nodePositions[node.id]
          if (!pos) return null

          const colorClass = NODE_COLORS[node.type] || NODE_COLORS.search
          const icon = NODE_ICONS[node.type] || '📄'
          const label = NODE_LABELS[node.type] || node.type

          return (
            <g
              key={node.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              className="cursor-pointer"
            >
              {/* Node background */}
              <rect
                width={pos.width}
                height={pos.height}
                rx={6}
                className={`fill-background stroke-2 ${colorClass}`}
              />

              {/* Priority indicator */}
              {node.priority > 0 && (
                <circle
                  cx={pos.width - 8}
                  cy={8}
                  r={4}
                  fill={node.priority > 0.7 ? 'hsl(142 76% 36%)' : node.priority > 0.4 ? 'hsl(38 92% 50%)' : 'hsl(0 84% 60%)'}
                />
              )}

              {/* Icon + Label */}
              <text x={8} y={16} className="text-xs" fill="currentColor">
                {icon}
              </text>
              <text x={24} y={16} className="text-[10px] font-medium fill-foreground">
                {label}
              </text>

              {/* Summary */}
              <text
                x={8}
                y={32}
                className="text-[9px] fill-muted-foreground"
              >
                {(node.summary || '').slice(0, 20)}...
              </text>

              {/* Node ID */}
              <text
                x={8}
                y={pos.height - 6}
                className="text-[8px] fill-muted-foreground/60"
              >
                {node.id.slice(0, 12)}...
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
