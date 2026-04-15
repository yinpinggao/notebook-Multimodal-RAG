'use client'

import { useState } from 'react'
import { VRAGMemoryNode, VRAGImageResult } from '@/lib/types/api'
import { useTranslation } from '@/lib/hooks/use-translation'
import { ImageIcon, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'

interface ImageEvidencePanelProps {
  dag: { nodes: VRAGMemoryNode[] }
  searchResults?: VRAGImageResult[]
  className?: string
}

export function ImageEvidencePanel({
  dag,
  searchResults = [],
  className = ''
}: ImageEvidencePanelProps) {
  const { t } = useTranslation()
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const [expandedImages, setExpandedImages] = useState<Set<string>>(new Set())

  // Collect all images from DAG nodes
  const imageNodes = dag.nodes.filter(n =>
    n.type === 'search' || n.type === 'bbox_crop'
  )

  const toggleNode = (nodeId: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev)
      if (next.has(nodeId)) {
        next.delete(nodeId)
      } else {
        next.add(nodeId)
      }
      return next
    })
  }

  const toggleImage = (imagePath: string) => {
    setExpandedImages(prev => {
      const next = new Set(prev)
      if (next.has(imagePath)) {
        next.delete(imagePath)
      } else {
        next.add(imagePath)
      }
      return next
    })
  }

  if (imageNodes.length === 0 && searchResults.length === 0) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center text-muted-foreground">
          <ImageIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="text-xs">{t.vrag?.noImages || 'No images retrieved yet'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-2 overflow-auto ${className}`}>
      {/* Images from search results */}
      {searchResults.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {t.vrag?.searchResults || 'Search Results'} ({searchResults.length})
          </h4>
          {searchResults.slice(0, 6).map((img, idx) => (
            <ImageCard
              key={img.chunk_id || `sr-${idx}`}
              image={img}
              isExpanded={expandedImages.has(img.chunk_id || `sr-${idx}`)}
              onToggle={() => toggleImage(img.chunk_id || `sr-${idx}`)}
            />
          ))}
        </div>
      )}

      {/* Images from DAG nodes */}
      {imageNodes.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {t.vrag?.evidenceNodes || 'Evidence Nodes'} ({imageNodes.length})
          </h4>
          {imageNodes.map((node) => (
            <div
              key={node.id}
              className="border rounded-lg overflow-hidden"
            >
              <button
                onClick={() => toggleNode(node.id)}
                className="w-full flex items-center justify-between px-3 py-2 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-sm flex-shrink-0">
                    {node.type === 'search' ? '🔍' : '✂️'}
                  </span>
                  <span className="text-xs font-medium truncate">
                    {node.summary?.slice(0, 40) || 'Node'}...
                  </span>
                </div>
                {expandedNodes.has(node.id) ? (
                  <ChevronUp className="h-3 w-3 flex-shrink-0" />
                ) : (
                  <ChevronDown className="h-3 w-3 flex-shrink-0" />
                )}
              </button>

              {expandedNodes.has(node.id) && (
                <div className="px-3 py-2 border-t bg-muted/20">
                  <p className="text-xs text-muted-foreground">
                    {node.key_insight || node.summary || 'No details'}
                  </p>
                  {(node.images?.length ?? 0) > 0 && (
                    <div className="mt-2 grid grid-cols-2 gap-1">
                      {node.images!.slice(0, 4).map((img, idx) => (
                        <div
                          key={idx}
                          className="aspect-square bg-muted rounded flex items-center justify-center overflow-hidden"
                        >
                          <ImageIcon className="h-4 w-4 text-muted-foreground" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ImageCard({
  image,
  isExpanded,
  onToggle
}: {
  image: VRAGImageResult
  isExpanded: boolean
  onToggle: () => void
}) {
  const [imgError, setImgError] = useState(false)

  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted/50 transition-colors"
      >
        <div className="flex-shrink-0 w-8 h-8 bg-muted rounded overflow-hidden flex items-center justify-center">
          {image.image_base64 && !imgError ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={`data:image/png;base64,${image.image_base64}`}
              alt={`Page ${image.page_no}`}
              className="w-full h-full object-cover"
              onError={() => setImgError(true)}
            />
          ) : (
            <ImageIcon className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
        <div className="flex-1 min-w-0 text-left">
          <p className="text-xs font-medium truncate">
            {image.summary?.slice(0, 40) || `Page ${image.page_no}`}
          </p>
          <p className="text-[10px] text-muted-foreground">
            Score: {image.score?.toFixed(3) || 'N/A'}
          </p>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-3 w-3 flex-shrink-0" />
        ) : (
          <ChevronDown className="h-3 w-3 flex-shrink-0" />
        )}
      </button>

      {isExpanded && (
        <div className="px-3 py-2 border-t bg-muted/20">
          {image.summary && (
            <p className="text-xs text-muted-foreground mb-2">{image.summary}</p>
          )}
          {image.image_path && (
            <a
              href={image.image_path}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] text-blue-500 hover:underline flex items-center gap-1"
            >
              <ExternalLink className="h-2 w-2" />
              Open image
            </a>
          )}
          <div className="mt-1 text-[10px] text-muted-foreground space-y-0.5">
            <p>Page: {image.page_no || 'N/A'}</p>
            <p>Source: {image.source_id || 'N/A'}</p>
            {image.bbox && image.bbox.length === 4 && (
              <p>BBox: [{image.bbox.map(v => v.toFixed(2)).join(', ')}]</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
