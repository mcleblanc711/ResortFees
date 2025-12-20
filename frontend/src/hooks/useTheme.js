import { useState, useEffect } from 'react'

const THEMES = ['dark', 'frutiger-aero', 'flat', 'cyberpunk', 'modern']
const STORAGE_KEY = 'hotel-policy-theme'
const DEFAULT_THEME = 'dark'

export function useTheme() {
  const [theme, setThemeState] = useState(() => {
    // Check localStorage on initial load
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored && THEMES.includes(stored)) {
        return stored
      }
    }
    return DEFAULT_THEME
  })

  useEffect(() => {
    // Apply theme to document
    document.documentElement.setAttribute('data-theme', theme)

    // Save to localStorage
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  const setTheme = (newTheme) => {
    if (THEMES.includes(newTheme)) {
      setThemeState(newTheme)
    }
  }

  return {
    theme,
    setTheme,
    availableThemes: THEMES,
  }
}

export default useTheme
