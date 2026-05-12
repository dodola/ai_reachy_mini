import React from 'react';
import { Box, Typography, Button, CircularProgress } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { ACCENT, accentAlpha, FONT_WEIGHT, RADIUS, STATUS, TYPO } from '@styles';

export type Step4Status = 'waiting' | 'searching' | 'found' | 'failed';

interface Step4ReconnectingProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  textPrimary: string;
  textSecondary: string;
  configuredNetwork: string | null;
  status: Step4Status;
  onRetry: () => void;
}

export default function Step4Reconnecting({
  textPrimary,
  textSecondary,
  configuredNetwork,
  status,
  onRetry,
}: Step4ReconnectingProps): React.ReactElement {
  const getStatusContent = (): React.ReactNode => {
    switch (status) {
      case 'searching':
        return (
          <>
            <CircularProgress size={32} sx={{ color: ACCENT.main, mb: 2 }} />
            <Typography sx={{ fontSize: TYPO.body, color: textSecondary, lineHeight: 1.6 }}>
              Verifying connection to{' '}
              <strong style={{ color: textPrimary }}>{configuredNetwork || 'network'}</strong>...
            </Typography>
            <Typography sx={{ fontSize: TYPO.xs, color: textSecondary, mt: 1, opacity: 0.7 }}>
              This may take a few seconds
            </Typography>
          </>
        );

      case 'found':
        return (
          <>
            <CheckCircleIcon sx={{ fontSize: TYPO.hero, color: STATUS.success, mb: 1 }} />
            <Typography
              sx={{ fontSize: TYPO.md, fontWeight: FONT_WEIGHT.semibold, color: STATUS.success }}
            >
              Connected successfully!
            </Typography>
            <Typography sx={{ fontSize: TYPO.sm, color: textSecondary, mt: 1 }}>
              Reachy is now on {configuredNetwork}
            </Typography>
          </>
        );

      case 'failed':
        return (
          <>
            <Typography sx={{ fontSize: TYPO.body, color: textSecondary, mb: 1, lineHeight: 1.6 }}>
              Connection failed.
            </Typography>
            <Typography
              sx={{ fontSize: TYPO.sm, color: textSecondary, mb: 2, lineHeight: 1.5, opacity: 0.8 }}
            >
              Please check your WiFi password and try again.
            </Typography>
            <Button
              variant="outlined"
              size="small"
              onClick={onRetry}
              sx={{
                fontSize: TYPO.sm,
                fontWeight: FONT_WEIGHT.semibold,
                textTransform: 'none',
                borderColor: ACCENT.main,
                color: ACCENT.main,
                px: 2,
                py: 0.5,
                borderRadius: RADIUS.md,
                '&:hover': {
                  borderColor: ACCENT.dark,
                  bgcolor: accentAlpha(0.08),
                },
              }}
            >
              Try again
            </Button>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <Box
      sx={{
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
      }}
    >
      {getStatusContent()}
    </Box>
  );
}
