"use client";

import { useState, useRef, useEffect, useId } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertCircle,
  Bot,
  User,
  Send,
  Loader2,
  GitBranch,
  ImageIcon,
  MessageSquare,
  Trash2,
  RotateCcw,
  Network,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTranslation } from "@/lib/hooks/use-translation";
import { DAGViewer } from "./DAGViewer";
import { ImageEvidencePanel } from "./ImageEvidencePanel";
import { VRAGDAG, VRAGSession, VRAGImageResult } from "@/lib/types/api";
import { VRAGMessage } from "@/lib/hooks/useVRAGChat";

interface VRAGChatPanelProps {
  // Chat state from hook
  messages: VRAGMessage[];
  isStreaming: boolean;
  isComplete: boolean;
  error: string | null;
  dag: VRAGDAG;
  currentAnswer: string;
  sessions: VRAGSession[];
  currentSession?: VRAGSession;
  sessionId: string | null;
  loadingSessions: boolean;

  // Actions
  onSendMessage: (
    question: string,
    sourceIds?: string[],
    maxSteps?: number,
    context?: string,
  ) => void;
  onCancelStreaming: () => void;
  onSwitchSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onResetConversation: () => void;

  // Optional data
  searchResults?: VRAGImageResult[];
  getEvidenceImages?: () => VRAGImageResult[];
  sourceIds?: string[];
  inputDisabledReason?: string;
  className?: string;
}

export function VRAGChatPanel({
  messages,
  isStreaming,
  isComplete,
  error,
  dag,
  currentAnswer,
  sessions,
  sessionId,
  onSendMessage,
  onCancelStreaming,
  onSwitchSession,
  onDeleteSession,
  onResetConversation,
  searchResults = [],
  getEvidenceImages = () => [],
  sourceIds = [],
  inputDisabledReason,
  className = "",
}: VRAGChatPanelProps) {
  const { t } = useTranslation();
  const chatInputId = useId();
  const [input, setInput] = useState("");
  const [maxSteps, setMaxSteps] = useState(10);
  const context = "";
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollRef = useRef(true);
  const canSend = sourceIds.length > 0 && !inputDisabledReason;

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (!shouldAutoScrollRef.current) {
      return;
    }

    messagesEndRef.current?.scrollIntoView({
      behavior: messages.length > 0 ? "smooth" : "auto",
      block: "end",
    });
  }, [messages, currentAnswer]);

  useEffect(() => {
    const viewport = messagesEndRef.current?.closest(
      '[data-slot="scroll-area-viewport"]',
    ) as HTMLDivElement | null;

    if (!viewport) {
      return;
    }

    const updateScrollIntent = () => {
      const distanceFromBottom =
        viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
      shouldAutoScrollRef.current = distanceFromBottom < 96;
    };

    updateScrollIntent();
    viewport.addEventListener("scroll", updateScrollIntent, { passive: true });

    return () => {
      viewport.removeEventListener("scroll", updateScrollIntent);
    };
  }, []);

  useEffect(() => {
    shouldAutoScrollRef.current = true;
  }, [sessionId]);

  const handleSend = () => {
    if (input.trim() && !isStreaming && canSend) {
      shouldAutoScrollRef.current = true;
      onSendMessage(input.trim(), sourceIds, maxSteps, context);
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    const isMac =
      typeof navigator !== "undefined" &&
      navigator.userAgent.toUpperCase().indexOf("MAC") >= 0;
    const isModifierPressed = isMac ? e.metaKey : e.ctrlKey;

    if (e.key === "Enter" && isModifierPressed) {
      e.preventDefault();
      handleSend();
    }
  };

  const isMac =
    typeof navigator !== "undefined" &&
    navigator.userAgent.toUpperCase().indexOf("MAC") >= 0;
  const keyHint = isMac ? "⌘+Enter" : "Ctrl+Enter";

  return (
    <Card
      className={`flex h-full min-h-0 flex-1 flex-col overflow-hidden ${className}`}
    >
      <CardHeader className="pb-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Network className="h-5 w-5 text-blue-500" />
            {t.vrag?.title || "Visual RAG"}
            {isStreaming && (
              <Badge variant="secondary" className="text-xs gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                {t.vrag?.reasoning || "Reasoning..."}
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-1">
            {/* Session selector */}
            {sessions.length > 0 && (
              <select
                value={sessionId || ""}
                onChange={(e) => onSwitchSession(e.target.value)}
                className="text-xs border rounded px-2 py-1 bg-background"
                disabled={isStreaming}
              >
                <option value="">{t.vrag?.newSession || "New session"}</option>
                {sessions.map((s) => (
                  <option key={s.id || "session"} value={s.id || ""}>
                    {s.title || (s.id ? s.id.slice(0, 8) + "..." : "(no id)")}
                  </option>
                ))}
              </select>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={onResetConversation}
              title={t.vrag?.reset || "New conversation"}
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
                title={t.vrag?.deleteSession || "Delete session"}
                disabled={isStreaming}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            )}
          </div>
        </div>

        {/* Max steps indicator */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
          <span>
            {t.vrag?.maxSteps || "Max steps"}: {maxSteps}
          </span>
          <span>•</span>
          <span>
            {t.vrag?.nodes || "DAG nodes"}: {dag.nodes.length}
          </span>
          <span>•</span>
          <span>
            {t.vrag?.images || "Images"}: {searchResults.length}
          </span>
        </div>
      </CardHeader>

      <CardContent className="grid flex-1 min-h-0 grid-cols-1 overflow-hidden p-0 md:grid-cols-[minmax(0,1fr)_20rem] xl:grid-cols-[minmax(0,1fr)_22rem]">
        {/* Left: Chat Panel */}
        <div className="flex min-h-0 min-w-0 flex-col md:border-r">
          <ScrollArea className="flex-1 min-h-0 px-4">
            <div className="space-y-4 py-4">
              {messages.length === 0 ? (
                <div className="text-center text-muted-foreground py-12">
                  {canSend ? (
                    <>
                      <div className="relative mx-auto mb-5 w-20 h-20">
                        <div className="absolute inset-0 rounded-full bg-blue-100 dark:bg-blue-900/40 animate-pulse" />
                        <div className="relative flex items-center justify-center h-full">
                          <Network className="h-10 w-10 text-blue-500 dark:text-blue-400" />
                        </div>
                      </div>
                      <p className="text-sm font-medium mb-1.5">
                        {t.vrag?.startConversation ||
                          "Ask questions about visual content"}
                      </p>
                      <p className="text-xs text-muted-foreground/70 mb-5 max-w-xs mx-auto leading-relaxed">
                        {t.vrag?.exampleQuestions ||
                          "Explore charts, diagrams, and images in your documents"}
                      </p>
                      <div className="flex flex-wrap justify-center gap-2 max-w-sm mx-auto">
                        {[
                          "What charts are in this document?",
                          "Describe the diagrams on page 5",
                          "Find all images and their context",
                          "What visual elements support the main argument?",
                        ].map((q, i) => (
                          <button
                            key={i}
                            onClick={() => {
                              setInput(q);
                            }}
                            className="text-[11px] px-3 py-1.5 rounded-full border border-border hover:border-primary/50 hover:bg-primary/5 transition-colors text-left text-muted-foreground hover:text-foreground"
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-10 w-10 mx-auto mb-4 opacity-60" />
                      <p className="text-sm font-medium mb-1.5">
                        {t.vrag?.noVisualSourcesTitle ||
                          "No visual sources available"}
                      </p>
                      <p className="text-xs text-muted-foreground/70 max-w-xs mx-auto leading-relaxed">
                        {inputDisabledReason}
                      </p>
                    </>
                  )}
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 ${
                      message.type === "human" ? "justify-end" : "justify-start"
                    }`}
                  >
                    {message.type === "ai" && (
                      <div className="flex-shrink-0">
                        <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                          <Bot className="h-4 w-4" />
                        </div>
                      </div>
                    )}
                    <div className="flex flex-col gap-2 max-w-[80%]">
                      <div
                        className={`rounded-lg px-4 py-2 ${
                          message.type === "human"
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted"
                        }`}
                      >
                        {message.type === "ai" ? (
                          <VRAGAIMessage content={message.content} />
                        ) : (
                          <p className="text-sm break-all">{message.content}</p>
                        )}
                      </div>
                      <span className="text-[10px] text-muted-foreground px-1">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    {message.type === "human" && (
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
                      <Bot className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 max-w-[80%]">
                    <div className="rounded-lg px-4 py-2 bg-muted">
                      {currentAnswer ? (
                        <VRAGAIMessage content={currentAnswer} />
                      ) : (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          {t.vrag?.reasoning || "Reasoning..."}
                        </div>
                      )}
                    </div>
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
                <span className="text-muted-foreground">
                  {t.vrag?.steps || "Steps"}:
                </span>
                <select
                  value={maxSteps}
                  onChange={(e) => setMaxSteps(Number(e.target.value))}
                  className="border rounded px-1 py-0.5 bg-background"
                  disabled={isStreaming}
                >
                  {[5, 10, 15, 20].map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
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
                placeholder={
                  canSend
                    ? `${t.vrag?.placeholder || "Ask about visual content"} (${keyHint})`
                    : inputDisabledReason ||
                      t.vrag?.inputDisabledNoSources ||
                      "No indexed visual sources are available for this chat."
                }
                disabled={isStreaming || !canSend}
                className="flex-1 min-h-[40px] max-h-[100px] resize-none py-2 px-3 min-w-0"
                rows={1}
              />
              <Button
                onClick={isStreaming ? onCancelStreaming : handleSend}
                disabled={
                  (!input.trim() && !isStreaming) || (!canSend && !isStreaming)
                }
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
        <div className="hidden min-h-0 min-w-0 overflow-hidden bg-card/30 md:flex md:flex-col">
          <Tabs
            defaultValue="dag"
            className="flex min-h-0 flex-1 flex-col overflow-hidden"
          >
            <TabsList className="w-full justify-start rounded-none border-b border-border/50 px-2 h-10 bg-transparent">
              <TabsTrigger
                value="dag"
                className="text-xs gap-1.5 h-8 data-[state=active]:bg-accent data-[state=active]:text-accent-foreground"
              >
                <GitBranch className="h-3 w-3" />
                {t.vrag?.dag || "DAG"}
              </TabsTrigger>
              <TabsTrigger
                value="images"
                className="text-xs gap-1.5 h-8 data-[state=active]:bg-accent data-[state=active]:text-accent-foreground"
              >
                <ImageIcon className="h-3 w-3" />
                {t.vrag?.images || "Images"}
              </TabsTrigger>
              <TabsTrigger
                value="messages"
                className="text-xs gap-1.5 h-8 data-[state=active]:bg-accent data-[state=active]:text-accent-foreground"
              >
                <MessageSquare className="h-3 w-3" />
                {t.vrag?.messages || "Msgs"}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="dag" className="m-0 min-h-0 overflow-hidden">
              <DAGViewer dag={dag} className="h-full" />
            </TabsContent>

            <TabsContent value="images" className="m-0 min-h-0 overflow-hidden">
              <ImageEvidencePanel
                dag={dag}
                searchResults={getEvidenceImages()}
                className="h-full"
              />
            </TabsContent>

            <TabsContent
              value="messages"
              className="m-0 min-h-0 overflow-hidden"
            >
              <div className="h-full overflow-auto p-2">
                <div className="space-y-2">
                  {dag.nodes.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <MessageSquare className="h-8 w-8 text-muted-foreground/30 mb-2" />
                      <p className="text-xs text-muted-foreground/60">
                        {t.vrag?.noMessages || "No reasoning steps yet"}
                      </p>
                      <p className="text-[10px] text-muted-foreground/40 mt-1">
                        Ask a question to see reasoning steps
                      </p>
                    </div>
                  ) : (
                    dag.nodes.map((node) => (
                      <div
                        key={node.id}
                        className="border border-border/60 rounded-lg p-2.5 bg-card hover:border-border transition-colors"
                      >
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/70">
                            {node.type?.replace("_", " ") || "node"}
                          </span>
                          {node.priority > 0 && (
                            <Badge
                              variant="outline"
                              className="text-[9px] h-4 px-1 font-medium"
                            >
                              {(node.priority * 100).toFixed(0)}%
                            </Badge>
                          )}
                        </div>
                        <p className="text-[11px] text-foreground/80 leading-relaxed line-clamp-3">
                          {node.summary || node.key_insight || "No summary"}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </CardContent>
    </Card>
  );
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
          ul: ({ children }) => (
            <ul className="mb-3 space-y-0.5">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-3 space-y-0.5">{children}</ol>
          ),
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto">
              <table className="min-w-full border-collapse border border-border">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted">{children}</thead>
          ),
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => (
            <tr className="border-b border-border">{children}</tr>
          ),
          th: ({ children }) => (
            <th className="border border-border px-2 py-1 text-left font-semibold text-xs">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-border px-2 py-1 text-xs">
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
