import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react'

export type BirdeyeTheme = 'sunburst' | 'ember' | 'tide' | 'midnight'

type ThemeContextValue = {
  theme: BirdeyeTheme
  setTheme: (theme: BirdeyeTheme) => void
}

const THEME_STORAGE_KEY = 'birdeye-theme'
const ThemeContext = createContext<ThemeContextValue | null>(null)

const applyThemeToDocument = (theme: BirdeyeTheme) => {
  document.documentElement.dataset.theme = theme
}

export const ThemeProvider = ({ children }: PropsWithChildren) => {
  const [theme, setThemeState] = useState<BirdeyeTheme>('sunburst')

  useEffect(() => {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY) as BirdeyeTheme | null
    const initialTheme = stored ?? 'sunburst'
    setThemeState(initialTheme)
    applyThemeToDocument(initialTheme)
  }, [])

  const setTheme = (nextTheme: BirdeyeTheme) => {
    setThemeState(nextTheme)
    window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme)
    applyThemeToDocument(nextTheme)
  }

  const value = useMemo(() => ({ theme, setTheme }), [theme])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export const useTheme = () => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}
