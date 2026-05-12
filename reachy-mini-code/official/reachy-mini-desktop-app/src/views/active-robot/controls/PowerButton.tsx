import React from 'react';
import { IconButton, CircularProgress } from '@mui/material';
import PowerSettingsNewOutlinedIcon from '@mui/icons-material/PowerSettingsNewOutlined';
import { ACCENT, DURATION, EASING, accentAlpha } from '@styles/tokens';
import { useAppPalette } from '@styles';

export interface PowerButtonProps {
  onStopDaemon: () => void;
  isStopping: boolean;
  isBusy: boolean;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
}

/**
 * Power Button Component - Top left corner power control
 *
 * Triggers the full shutdown sequence: sleep animation → disable motors → kill daemon
 * Disabled when robot is busy or already stopping.
 */
export default function PowerButton({
  onStopDaemon,
  isStopping,
  isBusy,
}: PowerButtonProps): React.ReactElement {
  const palette = useAppPalette();
  const canPowerOff = !isStopping && !isBusy;

  return (
    <IconButton
      onClick={onStopDaemon}
      disabled={!canPowerOff}
      sx={{
        position: 'absolute',
        top: 12,
        left: 12,
        bgcolor: palette.surfaceCard,
        color: ACCENT.main,
        width: 36,
        height: 36,
        border: `1px solid ${accentAlpha(palette.isDark ? 0.5 : 0.4)}`,
        backdropFilter: 'blur(10px)',
        transition: `transform ${DURATION.medium}ms ${EASING.standard}, opacity ${DURATION.medium}ms ${EASING.standard}`,
        opacity: canPowerOff ? 1 : 0.4,
        boxShadow: `0 2px 8px ${accentAlpha(palette.isDark ? 0.2 : 0.15)}`,
        zIndex: 20,
        '&:hover': {
          bgcolor: palette.accentSurfaceHover,
          transform: canPowerOff ? 'scale(1.08)' : 'none',
          borderColor: accentAlpha(palette.isDark ? 0.7 : 0.6),
          boxShadow: palette.shadowAccent,
        },
        '&:active': {
          transform: canPowerOff ? 'scale(0.95)' : 'none',
        },
        '&:disabled': {
          bgcolor: palette.isDark ? palette.surfaceSubtle : palette.surfaceCard,
          color: palette.textMuted,
          borderColor: palette.border,
        },
      }}
      title={isStopping ? 'Stopping...' : isBusy ? 'Wait for robot...' : 'Power Off'}
    >
      {isStopping ? (
        <CircularProgress size={16} thickness={4} sx={{ color: palette.textMuted }} />
      ) : (
        <PowerSettingsNewOutlinedIcon sx={{ fontSize: 18 }} />
      )}
    </IconButton>
  );
}
