import {
  ACCENT,
  accentAlpha,
  blackAlpha,
  whiteAlpha,
  hexToRgba,
  STATUS,
  STATUS_TEXT,
  DANGER,
  DURATION,
  EASING,
  RADIUS,
} from './tokens';

/**
 * App-wide palette built on top of raw tokens. Pure function - no React
 * dependencies - so it can be called from anywhere (tests, non-React utils,
 * snapshot tooling).
 *
 * Naming convention:
 * - `accent*` = brand accent variants
 * - `text*`   = text colors
 * - `surface*`= backgrounds / cards
 * - `border*` = outlines / dividers
 * - `overlay*`= scrim / modal background
 */
export interface AppPalette {
  /** `true` when dark mode is active. Convenience flag to avoid re-passing `darkMode` everywhere. */
  isDark: boolean;

  /* --- ACCENT (orange) --- */
  accent: string;
  accentLight: string;
  accentDark: string;
  /**
   * High-contrast accent text for overlays and inline callouts.
   * Maps to `ACCENT.light` in dark mode and `ACCENT.dark` in light mode so the
   * accent stays readable against both surface types.
   */
  accentTextStrong: string;
  /** Subtle tinted background (e.g. filled chips). */
  accentSurface: string;
  /** Slightly stronger tinted background (e.g. hover state). */
  accentSurfaceHover: string;
  /** Pressed / active tinted background. */
  accentSurfaceActive: string;
  /** Soft border (idle accent elements). */
  accentBorder: string;
  /** Stronger border (hovered accent elements). */
  accentBorderStrong: string;
  /** Drop shadow for hovered / elevated accent elements. */
  accentGlow: string;
  /** Soft inner glow (inset shadows). */
  accentGlowSoft: string;

  /* --- TEXT --- */
  textPrimary: string;
  /** Secondary / body text. */
  textSecondary: string;
  /** Muted / placeholder / helper text. */
  textMuted: string;
  /** Very faint text (captions, footer labels). */
  textFaint: string;
  /** Text on disabled controls. */
  textDisabled: string;

  /* --- SURFACES --- */
  /** Page / root background (opaque). */
  surfaceBg: string;
  /** Card / panel background. */
  surfaceCard: string;
  /** Hovered card / panel background. */
  surfaceCardHover: string;
  /** Subtle section / row background. */
  surfaceSubtle: string;

  /* --- BORDERS --- */
  border: string;
  borderStrong: string;
  divider: string;

  /* --- OVERLAYS --- */
  overlayScrim: string;
  overlayScrimStrong: string;

  /* --- SHADOWS --- */
  shadowSm: string;
  shadowMd: string;
  shadowLg: string;
  /** Shadow used to lift a focused accent element above its surroundings. */
  shadowAccent: string;

  /* --- STATUS (base) --- */
  statusSuccess: string;
  statusError: string;
  statusWarning: string;
  statusInfo: string;
  /** Neutral grey for "stopped" / "not_initialized" lifecycle states. */
  statusNeutral: string;
  /** Purple for "busy" / "moving" / "executing" / "app-running" states. */
  statusBusy: string;

  /* --- STATUS (tinted surfaces, borders, readable text) ---
   * Used by toasts, alert banners, chip pills, status badges.
   * `*Surface` sits behind text, `*Border` outlines the tile, `*Text` is the
   * readable accent on top of the surface. */
  statusSuccessSurface: string;
  statusSuccessBorder: string;
  statusSuccessText: string;
  statusErrorSurface: string;
  statusErrorSurfaceHover: string;
  statusErrorBorder: string;
  statusErrorText: string;
  statusWarningSurface: string;
  statusWarningBorder: string;
  statusWarningText: string;
  statusInfoSurface: string;
  statusInfoBorder: string;
  statusInfoText: string;
  statusNeutralSurface: string;
  statusNeutralBorder: string;
  statusNeutralText: string;
  statusBusySurface: string;
  statusBusyBorder: string;
  statusBusyText: string;

  /* --- DANGER (destructive actions) ---
   * Warmer and lighter than `statusError`. Reserved for buttons like
   * "Reset", "Clear cache", "Delete" where we want to warn without screaming. */
  dangerText: string;
  dangerBorder: string;
  dangerSurfaceHover: string;

  /* --- GHOST (non-matching search results, etc.) --- */
  ghostBg: string;
  ghostBorder: string;
}

/**
 * Build the app palette for a given theme mode. Memoized by consumers
 * (see `useAppPalette`) so the reference stays stable while `darkMode` is
 * unchanged.
 */
export function buildAppPalette(isDark: boolean): AppPalette {
  return {
    isDark,

    accent: ACCENT.main,
    accentLight: ACCENT.light,
    accentDark: ACCENT.dark,
    accentTextStrong: isDark ? ACCENT.light : ACCENT.dark,
    accentSurface: accentAlpha(isDark ? 0.06 : 0.04),
    accentSurfaceHover: accentAlpha(isDark ? 0.12 : 0.1),
    accentSurfaceActive: accentAlpha(isDark ? 0.25 : 0.2),
    accentBorder: accentAlpha(isDark ? 0.25 : 0.3),
    accentBorderStrong: accentAlpha(isDark ? 0.5 : 0.6),
    accentGlow: `0 6px 24px ${accentAlpha(0.35)}`,
    accentGlowSoft: accentAlpha(0.15),

    textPrimary: isDark ? '#f5f5f5' : '#333',
    textSecondary: isDark ? whiteAlpha(0.7) : blackAlpha(0.6),
    textMuted: isDark ? whiteAlpha(0.5) : blackAlpha(0.4),
    textFaint: isDark ? whiteAlpha(0.35) : blackAlpha(0.3),
    textDisabled: isDark ? whiteAlpha(0.3) : blackAlpha(0.2),

    surfaceBg: isDark ? '#0f0f0f' : '#ffffff',
    surfaceCard: isDark ? 'rgba(25,25,25,0.95)' : 'rgba(255,255,255,0.95)',
    surfaceCardHover: isDark ? 'rgba(35,35,35,0.95)' : 'rgba(250,250,250,0.95)',
    surfaceSubtle: isDark ? whiteAlpha(0.03) : blackAlpha(0.02),

    border: isDark ? whiteAlpha(0.08) : blackAlpha(0.1),
    borderStrong: isDark ? whiteAlpha(0.15) : blackAlpha(0.15),
    divider: isDark ? whiteAlpha(0.12) : blackAlpha(0.12),

    overlayScrim: isDark ? blackAlpha(0.5) : blackAlpha(0.3),
    overlayScrimStrong: isDark ? blackAlpha(0.75) : blackAlpha(0.5),

    shadowSm: isDark ? `0 2px 8px ${blackAlpha(0.25)}` : `0 2px 8px ${blackAlpha(0.08)}`,
    shadowMd: isDark ? `0 4px 20px ${blackAlpha(0.4)}` : `0 4px 20px ${blackAlpha(0.08)}`,
    shadowLg: isDark ? `0 8px 32px ${blackAlpha(0.4)}` : `0 8px 32px ${blackAlpha(0.05)}`,
    shadowAccent: `0 4px 12px ${accentAlpha(0.25)}`,

    statusSuccess: STATUS.success,
    statusError: STATUS.error,
    statusWarning: STATUS.warning,
    statusInfo: STATUS.info,
    statusNeutral: STATUS.neutral,
    statusBusy: STATUS.busy,

    statusSuccessSurface: hexToRgba(STATUS.success, isDark ? 0.15 : 0.1),
    statusSuccessBorder: hexToRgba(STATUS.success, isDark ? 0.4 : 0.3),
    statusSuccessText: isDark ? STATUS_TEXT.success.light : STATUS_TEXT.success.dark,

    statusErrorSurface: hexToRgba(STATUS.error, isDark ? 0.15 : 0.1),
    statusErrorSurfaceHover: hexToRgba(STATUS.error, isDark ? 0.22 : 0.15),
    statusErrorBorder: hexToRgba(STATUS.error, isDark ? 0.4 : 0.3),
    statusErrorText: isDark ? STATUS_TEXT.error.light : STATUS_TEXT.error.dark,

    statusWarningSurface: hexToRgba(STATUS.warning, isDark ? 0.15 : 0.1),
    statusWarningBorder: hexToRgba(STATUS.warning, isDark ? 0.4 : 0.3),
    statusWarningText: isDark ? STATUS_TEXT.warning.light : STATUS_TEXT.warning.dark,

    statusInfoSurface: hexToRgba(STATUS.info, isDark ? 0.15 : 0.1),
    statusInfoBorder: hexToRgba(STATUS.info, isDark ? 0.4 : 0.3),
    statusInfoText: isDark ? STATUS_TEXT.info.light : STATUS_TEXT.info.dark,

    statusNeutralSurface: hexToRgba(STATUS.neutral, isDark ? 0.15 : 0.1),
    statusNeutralBorder: hexToRgba(STATUS.neutral, isDark ? 0.4 : 0.3),
    statusNeutralText: isDark ? STATUS_TEXT.neutral.light : STATUS_TEXT.neutral.dark,

    statusBusySurface: hexToRgba(STATUS.busy, isDark ? 0.15 : 0.1),
    statusBusyBorder: hexToRgba(STATUS.busy, isDark ? 0.4 : 0.3),
    statusBusyText: isDark ? STATUS_TEXT.busy.light : STATUS_TEXT.busy.dark,

    dangerText: isDark ? DANGER.light : DANGER.dark,
    dangerBorder: isDark ? hexToRgba(DANGER.light, 0.5) : hexToRgba(DANGER.dark, 0.5),
    dangerSurfaceHover: isDark ? hexToRgba(DANGER.light, 0.1) : hexToRgba(DANGER.dark, 0.08),

    ghostBorder: isDark ? whiteAlpha(0.05) : blackAlpha(0.04),
    ghostBg: isDark ? whiteAlpha(0.02) : blackAlpha(0.01),
  };
}

/**
 * Convenience re-export of a fully-typed "tokens" bag so consumers that
 * already have a palette can grab the primitive tokens from a single import.
 */
export const TOKENS = {
  duration: DURATION,
  easing: EASING,
  radius: RADIUS,
} as const;

export type AppTokens = typeof TOKENS;
