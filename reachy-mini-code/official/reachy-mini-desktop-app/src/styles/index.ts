/**
 * Single entry point for the app's style system.
 *
 * - `tokens` contains raw primitives (colors, radii, durations, easings).
 * - `palette` derives theme-mode-aware colors (dark / light).
 * - `useAppPalette` is the React hook that components should consume.
 *
 * Usage:
 * ```ts
 * import { useAppPalette, DURATION, EASING } from '@/styles';
 * ```
 */
export * from './tokens';
export * from './palette';
export { useAppPalette } from './useAppPalette';
export { scrollbarSx } from './scrollbar';
export type { ScrollbarOptions } from './scrollbar';
