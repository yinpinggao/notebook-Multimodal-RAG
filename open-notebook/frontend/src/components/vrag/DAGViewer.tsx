"use client";

import { useMemo, useState } from "react";
import { VRAGDAG, VRAGMemoryNode } from "@/lib/types/api";
import { useTranslation } from "@/lib/hooks/use-translation";
import {
  Search,
  Scissors,
  FileText,
  CheckCircle2,
  GitBranch,
  Eye,
  TrendingUp,
  Layers,
} from "lucide-react";

interface DAGViewerProps {
  dag: VRAGDAG;
  className?: string;
}

const NODE_CONFIG: Record<
  string,
  {
    icon: typeof Search;
    color: { bg: string; border: string; text: string; icon: string };
    label: string;
  }
> = {
  search: {
    icon: Search,
    color: {
      bg: "bg-blue-50 dark:bg-blue-950/40",
      border: "border-blue-300 dark:border-blue-700",
      text: "text-blue-700 dark:text-blue-300",
      icon: "text-blue-500 dark:text-blue-400",
    },
    label: "Search",
  },
  bbox_crop: {
    icon: Scissors,
    color: {
      bg: "bg-purple-50 dark:bg-purple-950/40",
      border: "border-purple-300 dark:border-purple-700",
      text: "text-purple-700 dark:text-purple-300",
      icon: "text-purple-500 dark:text-purple-400",
    },
    label: "Crop",
  },
  summarize: {
    icon: FileText,
    color: {
      bg: "bg-amber-50 dark:bg-amber-950/40",
      border: "border-amber-300 dark:border-amber-700",
      text: "text-amber-700 dark:text-amber-300",
      icon: "text-amber-500 dark:text-amber-400",
    },
    label: "Summarize",
  },
  answer: {
    icon: CheckCircle2,
    color: {
      bg: "bg-emerald-50 dark:bg-emerald-950/40",
      border: "border-emerald-300 dark:border-emerald-700",
      text: "text-emerald-700 dark:text-emerald-300",
      icon: "text-emerald-500 dark:text-emerald-400",
    },
    label: "Answer",
  },
};

function getPriorityColor(priority: number): string {
  if (priority >= 0.7) return "text-emerald-500";
  if (priority >= 0.4) return "text-amber-500";
  return "text-red-500";
}

function getPriorityBg(priority: number): string {
  if (priority >= 0.7) return "bg-emerald-100 dark:bg-emerald-900/40";
  if (priority >= 0.4) return "bg-amber-100 dark:bg-amber-900/40";
  return "bg-red-100 dark:bg-red-900/40";
}

// Node detail card shown when a node is selected
function NodeDetailCard({
  node,
  onClose,
}: {
  node: VRAGMemoryNode;
  onClose: () => void;
}) {
  const config = NODE_CONFIG[node.type] || NODE_CONFIG.search;
  const Icon = config.icon;

  return (
    <div className="absolute inset-x-2 bottom-2 bg-background/95 backdrop-blur-sm border border-border rounded-lg shadow-lg p-3 z-10 max-h-[180px] overflow-auto">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div
            className={`p-1.5 rounded-md ${config.color.bg} ${config.color.icon}`}
          >
            <Icon className="h-3.5 w-3.5" />
          </div>
          <span className={`text-xs font-semibold ${config.color.text}`}>
            {config.label}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground text-xs"
        >
          ✕
        </button>
      </div>

      <p className="text-xs text-foreground mb-1.5 leading-relaxed">
        {node.summary || node.key_insight || "No summary available"}
      </p>

      <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
        {node.priority > 0 && (
          <span
            className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full ${getPriorityBg(
              node.priority,
            )} ${getPriorityColor(node.priority)}`}
          >
            <TrendingUp className="h-2.5 w-2.5" />
            {(node.priority * 100).toFixed(0)}%
          </span>
        )}
        {node.images?.length > 0 && (
          <span className="inline-flex items-center gap-0.5">
            <Eye className="h-2.5 w-2.5" />
            {node.images.length} img
          </span>
        )}
        <span className="font-mono opacity-60">{node.id.slice(0, 16)}...</span>
      </div>
    </div>
  );
}

export function DAGViewer({ dag, className = "" }: DAGViewerProps) {
  const { t } = useTranslation();
  const [selectedNode, setSelectedNode] = useState<VRAGMemoryNode | null>(null);

  // Build a hierarchical tree layout from the DAG
  const layout = useMemo(() => {
    if (dag.nodes.length === 0) return null;

    // Build adjacency list
    const children: Record<string, string[]> = {};
    const nodeMap: Record<string, VRAGMemoryNode> = {};

    for (const node of dag.nodes) {
      nodeMap[node.id] = node;
      children[node.id] = [];
    }

    for (const edge of dag.edges) {
      if (children[edge.target]) {
        children[edge.target].push(edge.source);
      }
    }

    // Find root nodes (nodes with no incoming edges)
    const targetIds = new Set(dag.edges.map((e) => e.target));
    const rootNodes = dag.nodes.filter((n) => !targetIds.has(n.id));

    // If no root found, use first node
    if (rootNodes.length === 0 && dag.nodes.length > 0) {
      rootNodes.push(dag.nodes[0]);
    }

    // Layout using a simple tree algorithm
    const NODE_WIDTH = 180;
    const NODE_HEIGHT = 72;
    const H_GAP = 60;
    const V_GAP = 20;

    const nodePositions: Record<string, { x: number; y: number }> = {};
    const visited = new Set<string>();

    function layoutNode(nodeId: string, x: number, y: number): number {
      if (visited.has(nodeId)) return y;
      visited.add(nodeId);

      const childIds = children[nodeId] || [];
      let currentY = y;

      if (childIds.length === 0) {
        nodePositions[nodeId] = { x, y: currentY };
        return currentY + NODE_HEIGHT + V_GAP;
      }

      // Layout children first
      let firstChildY = -1;
      let lastChildY = -1;

      for (const childId of childIds) {
        if (firstChildY === -1) {
          firstChildY = currentY;
        }
        currentY = layoutNode(childId, x + NODE_WIDTH + H_GAP, currentY);
        lastChildY = currentY - NODE_HEIGHT - V_GAP;
      }

      // Position this node centered between its children
      const centerY = (firstChildY + lastChildY) / 2;
      nodePositions[nodeId] = { x, y: centerY };
      visited.delete(nodeId); // Allow repositioning

      return lastChildY + NODE_HEIGHT + V_GAP;
    }

    let startY = 20;
    for (const root of rootNodes) {
      if (!visited.has(root.id)) {
        startY = layoutNode(root.id, 20, startY);
      }
    }

    // Handle any disconnected nodes
    for (const node of dag.nodes) {
      if (!nodePositions[node.id]) {
        nodePositions[node.id] = {
          x: 20,
          y: startY,
        };
        startY += NODE_HEIGHT + V_GAP;
      }
    }

    // Calculate bounds
    const maxX =
      Math.max(...Object.values(nodePositions).map((p) => p.x)) + NODE_WIDTH;
    const maxY =
      Math.max(...Object.values(nodePositions).map((p) => p.y)) + NODE_HEIGHT;

    return {
      nodePositions,
      NODE_WIDTH,
      NODE_HEIGHT,
      totalWidth: Math.max(maxX + 40, 400),
      totalHeight: Math.max(maxY + 40, 200),
      rootNodes,
    };
  }, [dag]);

  // Compute edge paths with bezier curves
  const edgePaths = useMemo(() => {
    if (!layout) return [];
    const { nodePositions, NODE_WIDTH, NODE_HEIGHT } = layout;

    return dag.edges
      .map((edge) => {
        const source = nodePositions[edge.source];
        const target = nodePositions[edge.target];
        if (!source || !target) return null;

        const x1 = source.x + NODE_WIDTH / 2;
        const y1 = source.y + NODE_HEIGHT;
        const x2 = target.x + NODE_WIDTH / 2;
        const y2 = target.y;

        // Bezier control points for a smooth curve
        const midY = (y1 + y2) / 2;
        return {
          source: edge.source,
          target: edge.target,
          path: `M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`,
          label: edge.relation,
        };
      })
      .filter(Boolean);
  }, [layout, dag.edges]);

  if (dag.nodes.length === 0) {
    return (
      <div
        className={`flex flex-col items-center justify-center h-full ${className}`}
      >
        <div className="text-center">
          <div className="relative mx-auto mb-4">
            <Layers className="h-14 w-14 text-muted-foreground/30 mx-auto" />
            <div className="absolute inset-0 flex items-center justify-center">
              <GitBranch className="h-6 w-6 text-muted-foreground/50" />
            </div>
          </div>
          <p className="text-sm font-medium text-muted-foreground/70">
            {t.vrag?.dagEmpty || "Reasoning DAG"}
          </p>
          <p className="text-xs text-muted-foreground/50 mt-1">
            {t.vrag?.dagEmptyHint || "DAG will appear as the agent reasons"}
          </p>
        </div>
      </div>
    );
  }

  if (!layout) return null;

  const { nodePositions, NODE_WIDTH, NODE_HEIGHT, totalWidth, totalHeight } =
    layout;

  return (
    <div
      className={`relative h-full min-h-0 w-full overflow-auto ${className}`}
    >
      {/* Stats bar */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-sm border-b border-border/50 px-3 py-1.5 flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <GitBranch className="h-3 w-3" />
          <span>
            {dag.nodes.length} {t.vrag?.nodes || "nodes"}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Eye className="h-3 w-3" />
          <span>
            {dag.nodes.reduce((acc, n) => acc + (n.images?.length || 0), 0)}{" "}
            {t.vrag?.images || "images"}
          </span>
        </div>
        {dag.edges.length > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <TrendingUp className="h-3 w-3" />
            <span>{dag.edges.length} edges</span>
          </div>
        )}
      </div>

      {/* SVG Canvas */}
      <svg
        width={totalWidth}
        height={totalHeight}
        className="min-w-full block"
        style={{ minHeight: totalHeight }}
      >
        <defs>
          {/* Gradient for edges */}
          <linearGradient id="edge-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop
              offset="0%"
              stopColor="hsl(var(--muted-foreground))"
              stopOpacity="0.6"
            />
            <stop
              offset="100%"
              stopColor="hsl(var(--muted-foreground))"
              stopOpacity="0.3"
            />
          </linearGradient>

          {/* Arrow marker */}
          <marker
            id="arrowhead"
            markerWidth="8"
            markerHeight="6"
            refX="6"
            refY="3"
            orient="auto"
          >
            <polygon
              points="0 0, 8 3, 0 6"
              fill="hsl(var(--muted-foreground))"
              fillOpacity="0.4"
            />
          </marker>

          {/* Glow filter for selected node */}
          <filter id="node-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow
              dx="0"
              dy="2"
              stdDeviation="3"
              floodColor="hsl(var(--primary))"
              floodOpacity="0.3"
            />
          </filter>
        </defs>

        {/* Edges */}
        {edgePaths.map(
          (edge) =>
            edge && (
              <g key={`${edge.source}-${edge.target}`}>
                {/* Shadow path */}
                <path
                  d={edge.path}
                  fill="none"
                  stroke="hsl(var(--background))"
                  strokeWidth={3}
                  strokeOpacity={0.5}
                />
                {/* Main edge path */}
                <path
                  d={edge.path}
                  fill="none"
                  stroke="url(#edge-gradient)"
                  strokeWidth={1.5}
                  markerEnd="url(#arrowhead)"
                  className="transition-all duration-300"
                />
                {/* Edge label */}
                {edge.label && (
                  <text
                    x={
                      (nodePositions[edge.source]?.x || 0) +
                      NODE_WIDTH / 2 +
                      ((nodePositions[edge.target]?.x || 0) -
                        (nodePositions[edge.source]?.x || 0)) /
                        2
                    }
                    y={
                      ((nodePositions[edge.source]?.y || 0) +
                        (nodePositions[edge.target]?.y || 0)) /
                        2 +
                      NODE_HEIGHT
                    }
                    className="text-[9px] fill-muted-foreground/60"
                    textAnchor="middle"
                  >
                    {edge.label}
                  </text>
                )}
              </g>
            ),
        )}

        {/* Nodes */}
        {dag.nodes.map((node) => {
          const pos = nodePositions[node.id];
          if (!pos) return null;

          const config = NODE_CONFIG[node.type] || NODE_CONFIG.search;
          const Icon = config.icon;
          const isSelected = selectedNode?.id === node.id;

          return (
            <g
              key={node.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              className="cursor-pointer"
              onClick={() => setSelectedNode(isSelected ? null : node)}
            >
              {/* Node shadow */}
              <rect
                x={2}
                y={2}
                width={NODE_WIDTH}
                height={NODE_HEIGHT}
                rx={8}
                className="fill-black/5 dark:fill-black/20"
              />

              {/* Node background */}
              <rect
                width={NODE_WIDTH}
                height={NODE_HEIGHT}
                rx={8}
                className={`${config.color.bg} ${config.color.border} ${
                  isSelected ? "stroke-2 stroke-primary" : "stroke-1"
                } ${isSelected ? "filter-[url(#node-glow)]" : ""}`}
                fillOpacity={isSelected ? 1 : 0.8}
              />

              {/* Left accent bar */}
              <rect
                x={0}
                y={0}
                width={4}
                height={NODE_HEIGHT}
                rx={8}
                className={`${config.color.icon} fill-current`}
              />

              {/* Icon */}
              <foreignObject x={12} y={14} width={24} height={24}>
                <div className="flex items-center justify-center">
                  <Icon className={`h-4 w-4 ${config.color.icon}`} />
                </div>
              </foreignObject>

              {/* Type label */}
              <text
                x={40}
                y={24}
                className={`text-[11px] font-semibold ${config.color.text}`}
              >
                {config.label}
              </text>

              {/* Priority indicator */}
              {node.priority > 0 && (
                <>
                  <rect
                    x={NODE_WIDTH - 42}
                    y={12}
                    width={36}
                    height={16}
                    rx={8}
                    className={`${getPriorityBg(node.priority)}`}
                  />
                  <text
                    x={NODE_WIDTH - 24}
                    y={23}
                    className={`text-[10px] font-semibold ${getPriorityColor(
                      node.priority,
                    )}`}
                    textAnchor="middle"
                  >
                    {(node.priority * 100).toFixed(0)}%
                  </text>
                </>
              )}

              {/* Summary (truncated) */}
              <foreignObject x={12} y={38} width={NODE_WIDTH - 24} height={28}>
                <div className="text-[10px] text-muted-foreground leading-relaxed overflow-hidden">
                  <p className="line-clamp-2">
                    {node.summary || node.key_insight || "Processing..."}
                  </p>
                </div>
              </foreignObject>
            </g>
          );
        })}
      </svg>

      {/* Node detail card */}
      {selectedNode && (
        <NodeDetailCard
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}
