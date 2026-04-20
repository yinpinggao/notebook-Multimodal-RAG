import '@testing-library/jest-dom'
import React from 'react'
import { vi } from 'vitest'
import { enUS } from '../lib/locales/en-US'

export const mockPush = vi.fn()
export const mockReplace = vi.fn()
export const mockPrefetch = vi.fn()
export const mockUsePathname = vi.fn(() => '')
export const mockUseSearchParams = vi.fn(() => new URLSearchParams())
export const mockUseParams = vi.fn(() => ({}))
export const mockRedirect = vi.fn()

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: mockPrefetch,
  }),
  usePathname: mockUsePathname,
  useSearchParams: mockUseSearchParams,
  useParams: mockUseParams,
  redirect: mockRedirect,
}))

vi.mock('next/image', () => ({
  default: (props: React.ImgHTMLAttributes<HTMLImageElement> & { fill?: boolean }) =>
    React.createElement('img', {
      ...Object.fromEntries(
        Object.entries(props).filter(([key]) => key !== 'fill')
      ),
      alt: props.alt || '',
    }),
}))

vi.mock('next/link', () => ({
  default: ({
    children,
    href,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    React.createElement('a', { href, ...props }, children)
  ),
}))

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // Deprecated
    removeListener: vi.fn(), // Deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock @/lib/hooks/use-translation with full locale structure
vi.mock('../lib/hooks/use-translation', () => {
  const t = (key: string) => key
  Object.assign(t, enUS)
  
  return {
    useTranslation: () => ({
      t,
      language: 'en-US',
      setLanguage: vi.fn(),
    }),
  }
})

// Mock @/lib/hooks/use-auth
vi.mock('@/lib/hooks/use-auth', () => ({
  useAuth: vi.fn(() => ({
    user: { id: '1', email: 'test@example.com' },
    logout: vi.fn(),
    isLoading: false,
  })),
}))

// Mock @/lib/stores/sidebar-store
vi.mock('@/lib/stores/sidebar-store', () => ({
  useSidebarStore: vi.fn(() => ({
    isCollapsed: false,
    toggleCollapse: vi.fn(),
  })),
}))

// Mock @/lib/hooks/use-create-dialogs
vi.mock('@/lib/hooks/use-create-dialogs', () => ({
  useCreateDialogs: vi.fn(() => ({
    openSourceDialog: vi.fn(),
    openNotebookDialog: vi.fn(),
    openPodcastDialog: vi.fn(),
  })),
}))
