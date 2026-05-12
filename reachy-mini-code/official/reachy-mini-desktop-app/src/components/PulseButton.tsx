import React, { type ReactNode } from 'react';
import { Button, type ButtonProps } from '@mui/material';
import type { SxProps, Theme } from '@mui/material/styles';
import { ACCENT, accentAlpha } from '@styles/tokens';
import { useAppPalette, TYPO, FONT_WEIGHT, RADIUS, DURATION, transition } from '@styles';

/**
 * `PulseButton` - Reusable button with orange halo pulse animation.
 *
 * Used across the app for primary CTAs:
 * - "Start" button (FindingRobotView)
 * - "Discover Apps" button
 * - "Controller" / "Expressions" buttons
 * - "Wake Up" button
 * - Permissions request button
 */

export type PulseButtonSize = 'small' | 'medium' | 'large';

export interface PulseButtonProps extends Omit<ButtonProps, 'size'> {
  children: ReactNode;
  pulse?: boolean;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  size?: PulseButtonSize;
}

const sizeStyles: Record<PulseButtonSize, Record<string, number | string>> = {
  small: { px: 2, py: 0.75, fontSize: TYPO.sm, borderRadius: RADIUS.md },
  medium: { px: 3, py: 1.25, fontSize: TYPO.md, borderRadius: RADIUS.xl },
  large: { px: 4, py: 1.5, fontSize: TYPO.lg, borderRadius: '14px' },
};

export default function PulseButton({
  children,
  onClick,
  disabled = false,
  pulse = true,
  startIcon,
  endIcon,
  fullWidth = false,
  size = 'medium',
  sx,
  ...props
}: PulseButtonProps): React.ReactElement {
  const palette = useAppPalette();
  const currentSize = sizeStyles[size] ?? sizeStyles.medium;
  const isDark = palette.isDark;

  const pulseStart = accentAlpha(isDark ? 0.4 : 0.3);
  const hoverShadow = `0 6px 16px ${accentAlpha(isDark ? 0.2 : 0.15)}`;
  const disabledAlpha = accentAlpha(isDark ? 0.3 : 0.4);

  const sxArray: SxProps<Theme> = [
    {
      ...currentSize,
      border: `1px solid ${ACCENT.main}`,
      color: ACCENT.main,
      bgcolor: 'transparent',
      fontWeight: FONT_WEIGHT.semibold,
      textTransform: 'none',
      transition: transition('all', DURATION.base),
      animation: disabled || !pulse ? 'none' : 'pulseHalo 3s ease-in-out infinite',
      '@keyframes pulseHalo': {
        '0%, 100%': {
          boxShadow: `0 0 0 0 ${pulseStart}`,
        },
        '50%': {
          boxShadow: `0 0 0 8px ${accentAlpha(0)}`,
        },
      },
      '&:hover': {
        bgcolor: accentAlpha(0.1),
        border: `1px solid ${ACCENT.main}`,
        boxShadow: hoverShadow,
        animation: 'none',
      },
      '&:disabled': {
        border: `1px solid ${disabledAlpha}`,
        color: disabledAlpha,
        animation: 'none',
      },
    },
    ...(Array.isArray(sx) ? sx : sx ? [sx] : []),
  ];

  return (
    <Button
      onClick={onClick}
      disabled={disabled}
      startIcon={startIcon}
      endIcon={endIcon}
      fullWidth={fullWidth}
      sx={sxArray}
      {...props}
    >
      {children}
    </Button>
  );
}
