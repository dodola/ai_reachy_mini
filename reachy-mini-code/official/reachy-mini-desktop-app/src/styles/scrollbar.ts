/**
 * Scoped scrollbar styling helpers.
 *
 * Replaces the 8+ hand-written `'&::-webkit-scrollbar': { ... }` blocks
 * scattered across the codebase. Pass the result as either a plain `sx`
 * spread (MUI) or a CSSObject (Emotion / styled).
 *
 * Usage (MUI):
 * ```tsx
 * <Box sx={{ overflowY: 'auto', ...scrollbarSx(palette) }}>…</Box>
 * ```
 *
 * Usage with overrides:
 * ```tsx
 * <Box sx={{ ...scrollbarSx(palette, { width: 8, radius: 4 }) }}>…</Box>
 * ```
 */

import { blackAlpha, whiteAlpha } from './tokens';
import type { AppPalette } from './palette';

export interface ScrollbarOptions {
  /** Track / thumb width in px. Defaults to 6 (matches the most common usage). */
  width?: number;
  /** Thumb border-radius in px. Defaults to 3. */
  radius?: number;
  /**
   * Thumb color when idle. Defaults to a theme-aware low-alpha grey
   * (light track on dark mode, dark track on light mode).
   */
  thumb?: string;
  /** Thumb color on hover. Defaults to a stronger alpha than `thumb`. */
  thumbHover?: string;
  /** Track color. Defaults to `transparent`. */
  track?: string;
}

/**
 * Returns an `sx`-compatible object implementing a consistent scrollbar look.
 * Only `::-webkit-scrollbar*` selectors are emitted; Firefox falls back to
 * `scrollbar-width: thin` for a similar effect.
 */
export function scrollbarSx(palette: AppPalette, options: ScrollbarOptions = {}) {
  const width = options.width ?? 6;
  const radius = options.radius ?? 3;
  const thumb = options.thumb ?? (palette.isDark ? whiteAlpha(0.12) : blackAlpha(0.15));
  const thumbHover = options.thumbHover ?? (palette.isDark ? whiteAlpha(0.25) : blackAlpha(0.3));
  const track = options.track ?? 'transparent';

  return {
    scrollbarWidth: 'thin' as const,
    scrollbarColor: `${thumb} ${track}`,
    '&::-webkit-scrollbar': { width, height: width },
    '&::-webkit-scrollbar-track': { background: track },
    '&::-webkit-scrollbar-thumb': {
      background: thumb,
      borderRadius: radius,
    },
    '&:hover::-webkit-scrollbar-thumb': {
      background: thumbHover,
    },
  } as const;
}
