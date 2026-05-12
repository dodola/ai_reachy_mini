import { useMemo } from 'react';
import useAppStore from '@store/useAppStore';
import { buildAppPalette, type AppPalette } from './palette';

/**
 * Returns the app-wide palette for the current theme mode.
 * Reactively re-renders the consumer when `darkMode` flips in the store.
 *
 * Prefer this hook over direct `darkMode ? A : B` ternaries in components.
 * If you need raw tokens (durations, radii, easings) that do not depend on
 * the theme mode, import them from `@/styles/tokens` directly.
 *
 * @example
 * ```tsx
 * const palette = useAppPalette();
 * <Box sx={{ bgcolor: palette.surfaceCard, color: palette.textPrimary }} />
 * ```
 */
export function useAppPalette(): AppPalette {
  const darkMode = useAppStore((state: { darkMode: boolean }) => state.darkMode);
  return useMemo(() => buildAppPalette(darkMode), [darkMode]);
}
