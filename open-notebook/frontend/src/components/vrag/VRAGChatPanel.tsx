'use client'

import { useState, useRef, useEffect, useId } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Bot,
  User,
  Send,
  Loader2,
  GitBranch,
  ImageIcon,
  MessageSquare,
  Clock,
  Trash2,
  RotateCcw,
  Network
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useTranslation } from '@/lib/hooks/use-translation'
import { DAGViewer } from './DAGViewer'
import { ImageEvidencePanel } from './ImageEvidencePanel'
import {
  VRAGMessage,
  VRAGSession,
  VRAGImageResult
} from '@/lib/types/api'

interface VRAGChatPanelProps {
  // Chat state from hook
  messages: VRAGMessage[]
  isStreaming: boolean
  isComplete: boolean
  error: string | null
  dag: { nodes: any[]; edges: any[] }
  currentAnswer: string
  sessions: VRAGSession[]
  currentSession?: VRAGSession
  sessionId: string | null
  loadingSessions: boolean

  // Actions
  onSendMessage: (question: string, sourceIds?: string[], maxSteps?: number, context?: string) => void
  onCancelStreaming: () => void
  onSwitchSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
  onResetConversation: () => void

  // Optional data
  searchResults?: VRAGImageResult[]
  sourceIds?: string[]
  className?: string
}

export function VRAGChatPanel({
  messages,
  isStreaming,
  isComplete,
  error,
  dag,
  currentAnswer,
  sessions,
  currentSession,
  sessionId,
  loadingSessions,
  onSendMessage,
  onCancelStreaming,
  onSwitchSession,
  onDeleteSession,
  onResetConversation,
  searchResults = [],
  sourceIds = [],
  className = ''
}: VRAGChatPanelProps) {
  const { t } = useTranslation()
  const chatInputId = useId()
  const [input, setInput] = useState('')
  const [maxSteps, setMaxSteps] = useState(10)
  const [context, setContext] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentAnswer])

  const handleSend = () => {
    if (input.trim() && !isStreaming) {
      onSendMessage(input.trim(), sourceIds, maxSteps, context)
      setInput('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    const isMac = typeof navigator !== 'undefined' && navigator.userAgent.toUpperCase().indexOf('MAC') >= 0
    const isModifierPressed = isMac ? e.metaKey : e.ctrlKey

    if (e.key === 'Enter' && isModifierPressed) {
      e.preventDefault()
      handleSend()
    }
  }

  const isMac = typeof navigator !== 'undefined' && navigator.userAgent.toUpperCase().indexOf('MAC') >= 0
  const keyHint = isMac ? '⌘+Enter' : 'Ctrl+Enter'

  return (
    <Card className={`flex flex-col h-full flex-1 overflow-hidden ${className}`}>
      <CardHeader className="pb-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Network className="h-5 w-5 text-blue-500" />
            {t.vrag?.title || 'Visual RAG'}
            {isStreaming && (
              <Badge variant="secondary" className="text-xs gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                {t.vrag?.reasoning || 'Reasoning...'}
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-1">
            {/* Session selector */}
            {sessions.length > 0 && (
              <select
                value={sessionId || ''}
                onChange={(e) => onSwitchSession(e.target.value)}
                className="text-xs border rounded px-2 py-1 bg-background"
                disabled={isStreaming}
              >
                <option value="">{t.vrag?.newSession || 'New session'}</option>
                {sessions.map((s) => (
                  <option key={s.id || 'session'} value={s.id || ''}>
                    {s.title || (s.id ? s.id.slice(0, 8) + '...' : '(no id)')}
                  </option>
                ))}
              </select>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={onResetConversation}
              title={t.vrag?.reset || 'New conversation'}
              disabled={isStreaming}
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
            {sessionId && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => onDeleteSession(sessionId)}
                title={t.vrag?.deleteSession || 'Delete session'}
                disabled={isStreaming}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            )}
          </div>
        </div>

        {/* Max steps indicator */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
          <span>{t.vrag?.maxSteps || 'Max steps'}: {maxSteps}</span>
          <span>•</span>
          <span>{t.vrag?.nodes || 'DAG nodes'}: {dag.nodes.length}</span>
          <span>•</span>
          <span>{t.vrag?.images || 'Images'}: {searchResults.length}</span>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex min-h-0 p-0">
        <div className="flex flex-1 min-h-0">
          {/* Left: Chat Panel */}
          <div className="flex-1 flex flex-col min-w-0 border-r">
            <ScrollArea className="flex-1 min-h-0 px-4">
              <div className="space-y-4 py-4">
                {messages.length === 0 ? (
                  <div className="text-center text-muted-foreground py-8">
                    <Network className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="text-sm">
                      {t.vrag?.startConversation || 'Ask questions about visual content in your documents'}
                    </p>
                    <p className="text-xs mt-2">
                      {t.vrag?.exampleQuestions || 'Try: "What charts are in this document?" or "Describe the diagram on page 5"'}
                    </p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex gap-3 ${
                        message.type === 'human' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      {message.type === 'ai' && (
                        <div className="flex-shrink-0">
                          <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                            <Bot className="h-4 w-4" />
                          </div>
                        </div>
                      )}
                      <div className="flex flex-col gap-2 max-w-[80%]">
                        <div
                          className={`rounded-lg px-4 py-2 ${
                            message.type === 'human'
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-muted'
                          }`}
                        >
                          {message.type === 'ai' ? (
                            <VRAGAIMessage content={message.content} />
                          ) : (
                            <p className="text-sm break-all">{message.content}</p>
                          )}
                        </div>
                        <span className="text-[10px] text-muted-foreground px-1">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      {message.type === 'human' && (
                        <div className="flex-shrink-0">
                          <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
                            <User className="h-4 w-4 text-primary-foreground" />
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}
                {isStreaming && !isComplete && (
                  <div className="flex gap-3 justify-start">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                        <Bot className="h-4 w-4" />
                      </div>
                    </div>
                    <div className="rounded-lg px-4 py-2 bg-muted">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                  </div>
                )}
                {error && (
                  <div className="rounded-lg px-4 py-2 bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                    {error}
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Chat input */}
            <div className="flex-shrink-0 p-4 space-y-3 border-t">
              {/* Settings row */}
              <div className="flex items-center gap-4 text-xs">
                <label className="flex items-center gap-1">
                  <span className="text-muted-foreground">{t.vrag?.steps || 'Steps'}:</span>
                  <select
                    value={maxSteps}
                    onChange={(e) => setMaxSteps(Number(e.target.value))}
                    className="border rounded px-1 py-0.5 bg-background"
                    disabled={isStreaming}
                  >
                    {[5, 10, 15, 20].map(v => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="flex gap-2 items-end min-w-0">
                <Textarea
                  id={chatInputId}
                  name="vrag-message"
                  autoComplete="off"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={`${t.vrag?.placeholder || 'Ask about visual content'} (${keyHint})`}
                  disabled={isStreaming}
                  className="flex-1 min-h-[40px] max-h-[100px] resize-none py-2 px-3 min-w-0"
                  rows={1}
                />
                <Button
                  onClick={isStreaming ? onCancelStreaming : handleSend}
                  disabled={!input.trim() && !isStreaming}
                  size="icon"
                  className="h-[40px] w-[40px] flex-shrink-0"
                >
                  {isStreaming ? (
                    <div className="h-4 w-4 rounded-full bg-destructive" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </div>

          {/* Right: DAG + Evidence Panel */}
          <div className="w-80 flex-shrink-0 hidden md:flex flex-col">
            <Tabs defaultValue="dag" className="flex-1 flex flex-col">
              <TabsList className="w-full justify-start rounded-none border-b px-2 h-9">
                <TabsTrigger value="dag" className="text-xs gap-1 h-7">
                  <GitBranch className="h-3 w-3" />
                  {t.vrag?.dag || 'DAG'}
                </TabsTrigger>
                <TabsTrigger value="images" className="text-xs gap-1 h-7">
                  <ImageIcon className="h-3 w-3" />
                  {t.vrag?.images || 'Images'}
                </TabsTrigger>
                <TabsTrigger value="messages" className="text-xs gap-1 h-7">
                  <MessageSquare className="h-3 w-3" />
                  {t.vrag?.messages || 'Msgs'}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="dag" className="flex-1 min-h-0 m-0 p-2">
                <DAGViewer
                  dag={dag}
                  className="h-full"
                />
              </TabsContent>

              <TabsContent value="images" className="flex-1 min-h-0 m-0 p-2">
                <ImageEvidencePanel
                  dag={dag}
                  searchResults={searchResults}
                  className="h-full"
                />
              </TabsContent>

              <TabsContent value="messages" className="flex-1 min-h-0 m-0 p-2 overflow-auto">
                <div className="space-y-2">
                  {dag.nodes.length === 0 ? (
                    <p className="text-xs text-muted-foreground text-center py-4">
                      {t.vrag?.noMessages || 'No reasoning steps yet'}
                    </p>
                  ) : (
                    dag.nodes.map((node) => (
                      <div
                        key={node.id}
                        className="border rounded-lg p-2"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium capitalize">
                            {node.type?.replace('_', ' ') || 'node'}
                          </span>
                          {node.priority > 0 && (
                            <Badge
                              variant="outline"
                              className="text-[9px] h-4 px-1"
                            >
                              {(node.priority * 100).toFixed(0)}%
                            </Badge>
                          )}
                        </div>
                        <p className="text-[10px] text-muted-foreground line-clamp-3">
                          {node.summary || node.key_insight || 'No summary'}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Helper component to render AI messages with markdown
function VRAGAIMessage({ content }: { content: string }) {
  return (
    <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none break-words prose-headings:font-semibold prose-a:text-blue-600 prose-a:break-all prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-p:mb-3 prose-p:leading-6 prose-li:mb-1">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-3">{children}</p>,
          h1: ({ children }) => <h1 className="mb-3 mt-5">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-2 mt-4">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-2 mt-3">{children}</h3>,
          h4: ({ children }) => <h4 className="mb-1 mt-3">{children}</h4>,
          li: ({ children }) => <li className="mb-0.5">{children}</li>,
          ul: ({ children }) => <ul className="mb-3 space-y-0.5">{children}</ul>,
          ol: ({ children }) => <ol className="mb-3 space-y-0.5">{children}</ol>,
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto">
              <table className="min-w-full border-collapse border border-border">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => <tr className="border-b border-border">{children}</tr>,
          th: ({ children }) => <th className="border border-border px-2 py-1 text-left font-semibold text-xs">{children}</th>,
          td: ({ children }) => <td className="border border-border px-2 py-1 text-xs">{children}</td>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
