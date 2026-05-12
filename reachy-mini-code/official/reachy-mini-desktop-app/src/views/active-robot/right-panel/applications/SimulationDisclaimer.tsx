import React, { useState, useEffect } from 'react';
import { Box, Typography, Button } from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { STATUS } from '@styles/tokens';
import { FONT_WEIGHT, RADIUS, TYPO, useAppPalette } from '@styles';

const STORAGE_KEY = 'simulation-disclaimer-accepted';

export interface SimulationDisclaimerProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  onAccept?: () => void;
}

/**
 * Simulation Mode Disclaimer Overlay (Compact)
 * Warns users that apps support is incomplete in simulation mode
 */
export default function SimulationDisclaimer({
  onAccept,
}: SimulationDisclaimerProps): React.ReactElement | null {
  const palette = useAppPalette();
  const [isVisible, setIsVisible] = useState<boolean>(false);

  useEffect(() => {
    const accepted = localStorage.getItem(STORAGE_KEY);
    setIsVisible(!accepted);
  }, []);

  const handleAccept = (): void => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setIsVisible(false);
    onAccept?.();
  };

  if (!isVisible) return null;

  const warningColor = STATUS.warning;

  return (
    <Box
      sx={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        // TODO(style-migration): scrim-over-card with 0.97 alpha isn't covered by palette.surfaceCard (0.95).
        bgcolor: palette.isDark ? 'rgba(26, 26, 26, 0.97)' : 'rgba(250, 250, 252, 0.97)',
        zIndex: 10,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2,
        gap: 1.5,
        borderRadius: '14px',
      }}
    >
      {/* Icon + Title row */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <WarningAmberIcon sx={{ fontSize: TYPO.xl, color: warningColor }} />
        <Typography
          sx={{
            fontSize: TYPO.body,
            fontWeight: FONT_WEIGHT.semibold,
            color: palette.textPrimary,
          }}
        >
          Simulation Mode
        </Typography>
      </Box>

      {/* Message */}
      <Typography
        sx={{
          fontSize: TYPO.xs,
          color: palette.textSecondary,
          textAlign: 'center',
          lineHeight: 1.6,
          maxWidth: 240,
        }}
      >
        Apps using <strong style={{ color: palette.textPrimary }}>camera</strong> or{' '}
        <strong style={{ color: palette.textPrimary }}>microphone</strong> won&apos;t work yet -
        coming soon!
      </Typography>

      {/* Button */}
      <Button
        size="small"
        onClick={handleAccept}
        sx={{
          mt: 0.5,
          color: warningColor,
          fontSize: TYPO.xs,
          fontWeight: FONT_WEIGHT.semibold,
          textTransform: 'none',
          px: 2,
          py: 0.5,
          borderRadius: RADIUS.sm,
          border: `1px solid ${palette.isDark ? 'rgba(245, 158, 11, 0.4)' : 'rgba(245, 158, 11, 0.5)'}`,
          '&:hover': {
            bgcolor: palette.isDark ? 'rgba(245, 158, 11, 0.15)' : 'rgba(245, 158, 11, 0.1)',
            borderColor: warningColor,
          },
        }}
      >
        Got it
      </Button>
    </Box>
  );
}
