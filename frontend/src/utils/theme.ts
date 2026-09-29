// Theme handling: light / dark / system (§ theme requirement).
// The resolved theme is applied as <html data-theme="light|dark">; a "system"
// preference follows the OS via matchMedia and reacts to live changes.
const STORAGE_KEY = 'ds_theme'

export type ThemePref = 'light' | 'dark' | 'system'

let media: MediaQueryList | null = null

function systemIsDark(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return true
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function resolve(pref: ThemePref): 'light' | 'dark' {
  if (pref === 'system') return systemIsDark() ? 'dark' : 'light'
  return pref
}

function paint(pref: ThemePref): void {
  const resolved = resolve(pref)
  document.documentElement.dataset.theme = resolved
  // Chrome / Safari theme-color meta (if present) follows the resolved theme.
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', resolved === 'dark' ? '#0c1220' : '#f4f6fb')
}

export function getStoredTheme(): ThemePref {
  if (typeof localStorage === 'undefined') return 'system'
  const v = localStorage.getItem(STORAGE_KEY)
  return v === 'light' || v === 'dark' || v === 'system' ? v : 'system'
}

export function setStoredTheme(pref: ThemePref): void {
  if (typeof localStorage !== 'undefined') localStorage.setItem(STORAGE_KEY, pref)
}

// Apply a preference now and keep "system" in sync with OS changes.
export function applyTheme(pref: ThemePref): void {
  setStoredTheme(pref)
  paint(pref)
  if (pref === 'system' && typeof window !== 'undefined' && window.matchMedia) {
    if (!media) media = window.matchMedia('(prefers-color-scheme: dark)')
    media.onchange = () => { if (getStoredTheme() === 'system') paint('system') }
  }
}

// Call once at startup.
export function initTheme(): void {
  applyTheme(getStoredTheme())
}
