'use client'

import { create } from 'zustand'

import type {
  EvidenceType,
  GlobalSection,
  ProjectSection,
  SearchMode,
} from '@/lib/zhiyancang/types'

interface ZycUIState {
  activeGlobalSection: GlobalSection
  activeProjectSection: ProjectSection
  mobileNavOpen: boolean
  workspaceLeftOpen: boolean
  workspaceRightOpen: boolean
  evidenceFilterOpen: boolean
  outputHistoryOpen: boolean
  demoMode: boolean
  activeEvidenceType: EvidenceType
  activeSearchMode: SearchMode
  selectedCompareSourceA: string
  selectedCompareSourceB: string
  selectedOutputTemplate: string
  selectedOutputVersionId: string
  workspaceRetrievalMode: SearchMode
  workspaceMemoryScope: string
  setActiveGlobalSection: (section: GlobalSection) => void
  setActiveProjectSection: (section: ProjectSection) => void
  setMobileNavOpen: (open: boolean) => void
  setWorkspaceLeftOpen: (open: boolean) => void
  setWorkspaceRightOpen: (open: boolean) => void
  setEvidenceFilterOpen: (open: boolean) => void
  setOutputHistoryOpen: (open: boolean) => void
  setDemoMode: (enabled: boolean) => void
  setActiveEvidenceType: (value: EvidenceType) => void
  setActiveSearchMode: (value: SearchMode) => void
  setSelectedCompareSourceA: (value: string) => void
  setSelectedCompareSourceB: (value: string) => void
  setSelectedOutputTemplate: (value: string) => void
  setSelectedOutputVersionId: (value: string) => void
  setWorkspaceRetrievalMode: (value: SearchMode) => void
  setWorkspaceMemoryScope: (value: string) => void
}

export const useZycUIStore = create<ZycUIState>((set) => ({
  activeGlobalSection: 'projects',
  activeProjectSection: 'overview',
  mobileNavOpen: false,
  workspaceLeftOpen: false,
  workspaceRightOpen: false,
  evidenceFilterOpen: false,
  outputHistoryOpen: false,
  demoMode: false,
  activeEvidenceType: 'docs',
  activeSearchMode: 'hybrid',
  selectedCompareSourceA: 's1',
  selectedCompareSourceB: 's2',
  selectedOutputTemplate: 'Defense Pitch',
  selectedOutputVersionId: 'v1',
  workspaceRetrievalMode: 'hybrid',
  workspaceMemoryScope: 'Project Memory',
  setActiveGlobalSection: (activeGlobalSection) => set({ activeGlobalSection }),
  setActiveProjectSection: (activeProjectSection) => set({ activeProjectSection }),
  setMobileNavOpen: (mobileNavOpen) => set({ mobileNavOpen }),
  setWorkspaceLeftOpen: (workspaceLeftOpen) => set({ workspaceLeftOpen }),
  setWorkspaceRightOpen: (workspaceRightOpen) => set({ workspaceRightOpen }),
  setEvidenceFilterOpen: (evidenceFilterOpen) => set({ evidenceFilterOpen }),
  setOutputHistoryOpen: (outputHistoryOpen) => set({ outputHistoryOpen }),
  setDemoMode: (demoMode) => set({ demoMode }),
  setActiveEvidenceType: (activeEvidenceType) => set({ activeEvidenceType }),
  setActiveSearchMode: (activeSearchMode) => set({ activeSearchMode }),
  setSelectedCompareSourceA: (selectedCompareSourceA) => set({ selectedCompareSourceA }),
  setSelectedCompareSourceB: (selectedCompareSourceB) => set({ selectedCompareSourceB }),
  setSelectedOutputTemplate: (selectedOutputTemplate) => set({ selectedOutputTemplate }),
  setSelectedOutputVersionId: (selectedOutputVersionId) => set({ selectedOutputVersionId }),
  setWorkspaceRetrievalMode: (workspaceRetrievalMode) => set({ workspaceRetrievalMode }),
  setWorkspaceMemoryScope: (workspaceMemoryScope) => set({ workspaceMemoryScope }),
}))
