import React from 'react';
import { Box, Typography, Button, CircularProgress } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import powerOnImage from '../../../assets/power-on.jpg';
import { ACCENT, accentAlpha, FONT_WEIGHT, RADIUS, STATUS, TYPO, useAppPalette } from '@styles';

interface Step1PowerOnProps {
  textPrimary: string;
  textSecondary: string;
  countdown: number;
  hasReachyHotspot: boolean;
  hotspotName?: string;
  isLocalScanning: boolean;
  onNext: () => void;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
}

export default function Step1PowerOn({
  textPrimary,
  textSecondary,
  countdown,
  hasReachyHotspot,
  hotspotName,
  isLocalScanning,
  onNext,
}: Step1PowerOnProps): React.ReactElement {
  const palette = useAppPalette();
  const isWaiting = countdown > 0 && !hasReachyHotspot;
  const timeoutReached = countdown === 0 && !hasReachyHotspot;

  return (
    <Box sx={{ width: '100%', textAlign: 'center' }}>
      {isWaiting ? (
        // Waiting for auto-detection
        <>
          <Typography sx={{ fontSize: TYPO.sm, color: textSecondary, mb: 2, lineHeight: 1.6 }}>
            Turn on your Reachy and wait. We're automatically detecting the WiFi hotspot it creates.
          </Typography>

          {/* Power on illustration */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              mb: 2,
            }}
          >
            <Box
              component="img"
              src={powerOnImage}
              alt="Power on Reachy"
              sx={{
                width: 140,
                height: 'auto',
                borderRadius: RADIUS.xl,
                border: `1px solid ${palette.border}`,
              }}
            />
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
            <CircularProgress size={16} sx={{ color: ACCENT.main }} />
            <Typography sx={{ fontSize: TYPO.xs, color: textSecondary }}>
              Detecting hotspot... ({countdown}s)
            </Typography>
          </Box>
        </>
      ) : timeoutReached ? (
        // Timeout - hotspot not detected
        <>
          <Typography sx={{ fontSize: TYPO.sm, color: textSecondary, mb: 2, lineHeight: 1.6 }}>
            Automatic detection didn't find a Reachy hotspot, but it may still exist on your
            network. Make sure your Reachy is powered on, then continue to the next step.
          </Typography>

          <Button
            variant="outlined"
            onClick={onNext}
            sx={{
              fontSize: TYPO.body,
              fontWeight: FONT_WEIGHT.semibold,
              textTransform: 'none',
              px: 3,
              py: 0.75,
              borderRadius: RADIUS.md,
              borderColor: ACCENT.main,
              color: ACCENT.main,
              '&:hover': {
                borderColor: ACCENT.dark,
                bgcolor: accentAlpha(0.08),
              },
            }}
          >
            Continue manually →
          </Button>
        </>
      ) : (
        // Hotspot detected (will auto-advance shortly)
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1.5 }}>
          <CheckCircleIcon sx={{ fontSize: TYPO.hero, color: STATUS.success }} />
          <Box sx={{ textAlign: 'center' }}>
            <Typography
              sx={{ fontSize: TYPO.md, fontWeight: FONT_WEIGHT.semibold, color: STATUS.success }}
            >
              {hotspotName || 'Hotspot'} detected!
            </Typography>
            <Typography sx={{ fontSize: TYPO.xs, color: textSecondary, mt: 0.5 }}>
              Moving to next step...
            </Typography>
          </Box>
        </Box>
      )}
    </Box>
  );
}
