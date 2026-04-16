'use client'

import { useState } from 'react'
import { VRAGMemoryNode, VRAGImageResult } from '@/lib/types/api'
import { useTranslation } from '@/lib/hooks/use-translation'
import {
  ImageIcon,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  ZoomIn,
  X,
  Search,
  Scissors,
  Star,
  FileText,
  Layers,
  Maximize2,
} from 'lucide-react'

interface ImageEvidencePanelProps {
  dag: { nodes: VRAGMemoryNode[] }
  searchResults?: VRAGImageResult[]
  className?: string
}

interface LightboxProps {
  image: VRAGImageResult
  onClose: () => void
}

function ImageLightbox({ image, onClose }: LightboxProps) {
  const imageUrl = image.file_url || image.image_path

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-white/80 hover:text-white p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
      >
        <X className="h-5 w-5" />
      </button>

      <div
        className="max-w-4xl max-h-[85vh] flex flex-col items-center"
        onClick={(e) => e.stopPropagation()}
      >
        {image.image_base64 ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={`data:image/png;base64,${image.image_base64}`}
            alt={`Page ${image.page_no}`}
            className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-2xl"
          />
        ) : imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={`Page ${image.page_no}`}
            className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-2xl"
            onError={(e) => {
              const target = e.target as HTMLImageElement
              target.style.display = 'none'
              const parent = target.parentElement
              if (parent) {
                parent.innerHTML =
                  '<div class="flex items-center justify-center h-64 text-white/50"><svg class="h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg></div>'
              }
            }}
          />
        ) : (
          <div className="flex items-center justify-center h-64 text-white/50">
            <ImageIcon className="h-16 w-16" />
          </div>
        )}

        <div className="mt-4 w-full bg-white/10 backdrop-blur-sm rounded-lg p-4 text-white">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium flex items-center gap-2">
              <ImageIcon className="h-4 w-4 opacity-70" />
              {image.summary?.slice(0, 80) || `Page ${image.page_no}`}
            </h3>
            {image.score && (
              <div className="flex items-center gap-1 text-xs bg-white/10 px-2 py-1 rounded-full">
                <Star className="h-3 w-3 text-amber-400" />
                <span>{(image.score * 100).toFixed(1)}%</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4 text-xs text-white/70">
            {image.page_no && <span>Page {image.page_no}</span>}
            {image.source_id && (
              <span className="truncate max-w-[200px]">
                Source: {image.source_id.split(':').pop() || image.source_id}
              </span>
            )}
            {image.bbox && image.bbox.length === 4 && (
              <span className="font-mono">
                BBox: [{image.bbox.map((v) => v.toFixed(0)).join(',')}]
              </span>
            )}
          </div>

          {image.summary && (
            <p className="mt-2 text-xs text-white/60 leading-relaxed">
              {image.summary}
            </p>
          )}

          {imageUrl && (
            <a
              href={imageUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-2 text-xs text-blue-300 hover:text-blue-200 transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              Open original
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

function ScoreBar({ score }: { score: number }) {
  const percentage = score * 100
  const color =
    score >= 0.8
      ? 'bg-emerald-500'
      : score >= 0.5
        ? 'bg-amber-500'
        : 'bg-blue-400'

  return (
    <div className="flex items-center gap-1.5">
      <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full ${color} transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-[10px] font-medium text-muted-foreground w-8 text-right">
        {(percentage).toFixed(0)}%
      </span>
    </div>
  )
}

function ImageCard({
  image,
  compact = false,
}: {
  image: VRAGImageResult
  compact?: boolean
}) {
  const [imgError, setImgError] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const imageUrl = image.file_url || image.image_path

  const hasImage =
    image.image_base64 && !imgError
      ? `data:image/png;base64,${image.image_base64}`
      : imageUrl && !imgError

  return (
    <>
      <div
        className={`border rounded-lg overflow-hidden transition-all hover:shadow-md ${
          compact ? 'bg-card' : 'bg-card'
        }`}
      >
        {/* Thumbnail */}
        <button
          onClick={() => setIsExpanded(true)}
          className="w-full relative overflow-hidden bg-muted/30"
          style={{ height: compact ? 80 : 120 }}
        >
          {hasImage ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={
                  image.image_base64 && !imgError
                    ? `data:image/png;base64,${image.image_base64}`
                    : imageUrl || ''
                }
                alt={`Page ${image.page_no}`}
                className="w-full h-full object-cover transition-transform hover:scale-105"
                onError={() => setImgError(true)}
              />
              <div className="absolute inset-0 flex items-center justify-center bg-black/0 hover:bg-black/20 transition-colors">
                <ZoomIn className="h-6 w-6 text-white opacity-0 hover:opacity-100 transition-opacity drop-shadow-lg" />
              </div>
            </>
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <ImageIcon className="h-8 w-8 text-muted-foreground/40" />
            </div>
          )}

          {/* Score badge */}
          {image.score && (
            <div className="absolute top-1.5 right-1.5 bg-black/60 backdrop-blur-sm text-white text-[9px] font-medium px-1.5 py-0.5 rounded-full flex items-center gap-0.5">
              <Star className="h-2.5 w-2.5 text-amber-400 fill-amber-400" />
              {(image.score * 100).toFixed(0)}%
            </div>
          )}

          {/* Page badge */}
          {image.page_no && (
            <div className="absolute bottom-1.5 left-1.5 bg-black/60 backdrop-blur-sm text-white text-[9px] px-1.5 py-0.5 rounded-full">
              p.{image.page_no}
            </div>
          )}

          {/* Expand hint */}
          <div className="absolute top-1.5 left-1.5 bg-black/40 backdrop-blur-sm text-white/70 text-[9px] px-1 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity">
            <Maximize2 className="h-2.5 w-2.5" />
          </div>
        </button>

        {/* Meta info */}
        {!compact && (
          <div className="p-2 space-y-1.5">
            <ScoreBar score={image.score || 0} />

            {image.summary && (
              <p className="text-[10px] text-muted-foreground line-clamp-2 leading-relaxed">
                {image.summary}
              </p>
            )}

            <div className="flex items-center justify-between text-[9px] text-muted-foreground/60">
              <span className="truncate max-w-[120px]">
                {image.source_id
                  ? image.source_id.split(':').pop()
                  : image.chunk_id?.slice(0, 8)}
              </span>
              {image.bbox && image.bbox.length === 4 && (
                <span className="font-mono flex-shrink-0">
                  [{image.bbox.map((v) => v.toFixed(0)).join(',')}]
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Lightbox */}
      {isExpanded && (
        <ImageLightbox image={image} onClose={() => setIsExpanded(false)} />
      )}
    </>
  )
}

function DAGNodeCard({
  node,
  isExpanded,
  onToggle,
  searchResults = [],
}: {
  node: VRAGMemoryNode
  isExpanded: boolean
  onToggle: () => void
  searchResults?: VRAGImageResult[]
}) {
  const Icon = node.type === 'search' ? Search : Scissors

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-card">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-muted/40 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <div
            className={`p-1 rounded-md flex-shrink-0 ${
              node.type === 'search'
                ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400'
                : 'bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400'
            }`}
          >
            <Icon className="h-3 w-3" />
          </div>
          <div className="min-w-0 flex-1 text-left">
            <p className="text-xs font-medium truncate">
              {node.summary?.slice(0, 50) || node.key_insight?.slice(0, 50) || 'Node'}
            </p>
            {node.images?.length ? (
              <p className="text-[10px] text-muted-foreground">
                {node.images.length} image{node.images.length > 1 ? 's' : ''}
              </p>
            ) : null}
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {node.priority > 0 && (
            <div
              className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                node.priority >= 0.7
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400'
                  : node.priority >= 0.4
                    ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400'
                    : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'
              }`}
            >
              {(node.priority * 100).toFixed(0)}%
            </div>
          )}
          {isExpanded ? (
            <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="px-3 pb-3 border-t border-border/50 bg-muted/10">
          <p className="text-[11px] text-muted-foreground mt-2 leading-relaxed">
            {node.key_insight || node.summary || 'No details available'}
          </p>

          {/* Image thumbnails */}
          {node.images && node.images.length > 0 && (
            <div className="mt-2">
              <p className="text-[10px] font-medium text-muted-foreground/70 mb-1.5">
                Images ({node.images.length})
              </p>
              <div className="grid grid-cols-3 gap-1">
                {node.images.slice(0, 6).map((imgPath, idx) => {
                  const imgData = searchResults.find(r => (
                    r.file_url === imgPath || r.image_path === imgPath
                  ))
                  return imgData ? (
                    <ImageCard key={idx} image={imgData} compact />
                  ) : (
                    <div
                      key={idx}
                      className="aspect-square bg-muted rounded overflow-hidden flex items-center justify-center"
                    >
                      <ImageIcon className="h-4 w-4 text-muted-foreground/40" />
                    </div>
                  )
                })}
                {node.images.length > 6 && (
                  <div className="aspect-square bg-muted rounded flex items-center justify-center text-[10px] text-muted-foreground">
                    +{node.images.length - 6}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function ImageEvidencePanel({
  dag,
  searchResults = [],
  className = '',
}: ImageEvidencePanelProps) {
  const { t } = useTranslation()
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const [activeSection, setActiveSection] = useState<'results' | 'nodes'>(
    searchResults.length > 0 ? 'results' : 'nodes'
  )

  // Collect all images from DAG nodes
  const imageNodes = dag.nodes.filter(
    (n) => n.type === 'search' || n.type === 'bbox_crop'
  )

  const toggleNode = (nodeId: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev)
      if (next.has(nodeId)) {
        next.delete(nodeId)
      } else {
        next.add(nodeId)
      }
      return next
    })
  }

  if (imageNodes.length === 0 && searchResults.length === 0) {
    return (
      <div className={`flex flex-col items-center justify-center h-full ${className}`}>
        <div className="text-center px-4">
          <div className="relative mx-auto mb-3">
            <ImageIcon className="h-12 w-12 text-muted-foreground/25 mx-auto" />
          </div>
          <p className="text-xs font-medium text-muted-foreground/60">
            {t.vrag?.noImages || 'No images retrieved yet'}
          </p>
          <p className="text-[10px] text-muted-foreground/40 mt-1">
            Images from indexed sources will appear here
          </p>
        </div>
      </div>
    )
  }

  const totalImages =
    searchResults.length +
    imageNodes.reduce((acc, n) => acc + (n.images?.length || 0), 0)

  return (
    <div className={`h-full flex flex-col ${className}`}>
      {/* Section switcher */}
      <div className="flex-shrink-0 flex items-center gap-1 px-2 py-1.5 border-b border-border/50">
        {searchResults.length > 0 && (
          <button
            onClick={() => setActiveSection('results')}
            className={`text-xs px-2.5 py-1 rounded-md transition-colors flex items-center gap-1 ${
              activeSection === 'results'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <Search className="h-3 w-3" />
            Results ({searchResults.length})
          </button>
        )}
        {imageNodes.length > 0 && (
          <button
            onClick={() => setActiveSection('nodes')}
            className={`text-xs px-2.5 py-1 rounded-md transition-colors flex items-center gap-1 ${
              activeSection === 'nodes' || searchResults.length === 0
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <Layers className="h-3 w-3" />
            Nodes ({imageNodes.length})
          </button>
        )}
        <div className="ml-auto text-[10px] text-muted-foreground flex items-center gap-1">
          <ImageIcon className="h-3 w-3" />
          {totalImages} total
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-2 space-y-3">
        {activeSection === 'results' && searchResults.length > 0 && (
          <div className="space-y-2">
            {searchResults.length > 0 && (
              <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground/70 px-1">
                <FileText className="h-3 w-3" />
                <span>Search results sorted by relevance</span>
              </div>
            )}
            <div className="grid grid-cols-2 gap-2">
              {searchResults.map((img, idx) => (
                <ImageCard key={img.chunk_id || `sr-${idx}`} image={img} />
              ))}
            </div>
          </div>
        )}

        {activeSection === 'nodes' && imageNodes.length > 0 && (
          <div className="space-y-2">
            {imageNodes.map((node) => (
              <DAGNodeCard
                key={node.id}
                node={node}
                isExpanded={expandedNodes.has(node.id)}
                onToggle={() => toggleNode(node.id)}
                searchResults={searchResults}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
