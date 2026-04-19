import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import {
  AssistantContextItem,
  AssistantMobileTab,
  AssistantView,
  DEFAULT_ASSISTANT_AGENT,
  DEFAULT_ASSISTANT_TAB,
  DEFAULT_ASSISTANT_VIEW,
  HarnessAgentId,
} from '@/lib/assistant-workspace'

interface AssistantWorkspaceStoreState {
  currentProjectId?: string
  currentAgent: HarnessAgentId
  currentThreadId?: string
  currentView: AssistantView
  knowledgeCollapsed: boolean
  memoryCollapsed: boolean
  mobileTab: AssistantMobileTab
  selectedContextItems: AssistantContextItem[]
  lastProjectId?: string
  setCurrentProject: (projectId?: string) => void
  setCurrentAgent: (agent: HarnessAgentId) => void
  setCurrentThread: (threadId?: string) => void
  setCurrentView: (view: AssistantView) => void
  setMobileTab: (tab: AssistantMobileTab) => void
  setKnowledgeCollapsed: (collapsed: boolean) => void
  setMemoryCollapsed: (collapsed: boolean) => void
  toggleKnowledgeCollapsed: () => void
  toggleMemoryCollapsed: () => void
  addContextItem: (item: AssistantContextItem) => void
  removeContextItem: (type: AssistantContextItem['type'], id: string) => void
  toggleContextItem: (item: AssistantContextItem) => void
  clearContextItems: () => void
  replaceContextItems: (items: AssistantContextItem[]) => void
  setLastProjectId: (projectId?: string) => void
}

export const useAssistantWorkspaceStore = create<AssistantWorkspaceStoreState>()(
  persist(
    (set, get) => ({
      currentProjectId: undefined,
      currentAgent: DEFAULT_ASSISTANT_AGENT,
      currentThreadId: undefined,
      currentView: DEFAULT_ASSISTANT_VIEW,
      knowledgeCollapsed: false,
      memoryCollapsed: false,
      mobileTab: DEFAULT_ASSISTANT_TAB,
      selectedContextItems: [],
      lastProjectId: undefined,
      setCurrentProject: (projectId) =>
        set((state) => ({
          currentProjectId: projectId,
          currentThreadId:
            state.currentProjectId && state.currentProjectId !== projectId
              ? undefined
              : state.currentThreadId,
          selectedContextItems:
            state.currentProjectId && state.currentProjectId !== projectId
              ? []
              : state.selectedContextItems,
        })),
      setCurrentAgent: (agent) => set({ currentAgent: agent }),
      setCurrentThread: (threadId) => set({ currentThreadId: threadId }),
      setCurrentView: (view) => set({ currentView: view }),
      setMobileTab: (tab) => set({ mobileTab: tab }),
      setKnowledgeCollapsed: (collapsed) => set({ knowledgeCollapsed: collapsed }),
      setMemoryCollapsed: (collapsed) => set({ memoryCollapsed: collapsed }),
      toggleKnowledgeCollapsed: () =>
        set((state) => ({ knowledgeCollapsed: !state.knowledgeCollapsed })),
      toggleMemoryCollapsed: () =>
        set((state) => ({ memoryCollapsed: !state.memoryCollapsed })),
      addContextItem: (item) =>
        set((state) => {
          const existing = state.selectedContextItems.find(
            (candidate) => candidate.type === item.type && candidate.id === item.id
          )
          if (existing) {
            return {
              selectedContextItems: state.selectedContextItems.map((candidate) =>
                candidate.type === item.type && candidate.id === item.id
                  ? { ...candidate, ...item }
                  : candidate
              ),
            }
          }
          return {
            selectedContextItems: [...state.selectedContextItems, item],
          }
        }),
      removeContextItem: (type, id) =>
        set((state) => ({
          selectedContextItems: state.selectedContextItems.filter(
            (item) => !(item.type === type && item.id === id)
          ),
        })),
      toggleContextItem: (item) => {
        const state = get()
        const exists = state.selectedContextItems.some(
          (candidate) => candidate.type === item.type && candidate.id === item.id
        )

        if (exists) {
          set({
            selectedContextItems: state.selectedContextItems.filter(
              (candidate) =>
                !(candidate.type === item.type && candidate.id === item.id)
            ),
          })
          return
        }

        set({
          selectedContextItems: [...state.selectedContextItems, item],
        })
      },
      clearContextItems: () => set({ selectedContextItems: [] }),
      replaceContextItems: (items) => set({ selectedContextItems: items }),
      setLastProjectId: (projectId) => set({ lastProjectId: projectId }),
    }),
    {
      name: 'assistant-workspace-storage',
      partialize: (state) => ({
        currentAgent: state.currentAgent,
        currentView: state.currentView,
        knowledgeCollapsed: state.knowledgeCollapsed,
        memoryCollapsed: state.memoryCollapsed,
        mobileTab: state.mobileTab,
        selectedContextItems: state.selectedContextItems,
        lastProjectId: state.lastProjectId,
      }),
    }
  )
)
