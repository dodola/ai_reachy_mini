import React from 'react';
import { Box, Typography, Button, CircularProgress } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import type { WifiRobotCompat } from '../../../hooks/system/useRobotDiscovery';
import { ACCENT, FONT_WEIGHT, RADIUS, STATUS, STATUS_TEXT, TYPO, hexToRgba } from '@styles';

interface Step5SuccessProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  textPrimary: string;
  textSecondary: string;
  wifiRobot: WifiRobotCompat;
  configuredNetwork: string | null;
  isConnecting: boolean;
  onConnect: () => void;
}

export default function Step5Success({
  textPrimary,
  textSecondary,
  wifiRobot,
  configuredNetwork,
  isConnecting,
  onConnect,
}: Step5SuccessProps): React.ReactElement {
  const isReachyFound = wifiRobot?.available && wifiRobot?.host;

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
      {isReachyFound ? (
        <>
          <CheckCircleIcon sx={{ fontSize: TYPO.hero, color: STATUS.success, mb: 1.5 }} />
          <Typography sx={{ fontSize: TYPO.sm, color: textSecondary, mb: 2, lineHeight: 1.6 }}>
            Your Reachy Mini is now connected to{' '}
            <strong style={{ color: textPrimary }}>{configuredNetwork || 'your network'}</strong>.
            <br />
            Detected at <strong style={{ color: textPrimary }}>{wifiRobot.host}</strong>.
          </Typography>

          <Button
            variant="outlined"
            onClick={onConnect}
            disabled={isConnecting}
            sx={{
              fontSize: TYPO.body,
              fontWeight: FONT_WEIGHT.semibold,
              textTransform: 'none',
              px: 3,
              py: 0.75,
              borderRadius: RADIUS.md,
              borderColor: STATUS.success,
              color: STATUS.success,
              '&:hover': {
                borderColor: STATUS_TEXT.success.dark,
                bgcolor: hexToRgba(STATUS.success, 0.08),
              },
            }}
          >
            {isConnecting ? (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CircularProgress size={14} sx={{ color: 'inherit' }} />
                Connecting...
              </Box>
            ) : (
              'Connect Now'
            )}
          </Button>
        </>
      ) : (
        <>
          <CircularProgress size={32} sx={{ color: ACCENT.main, mb: 2 }} />
          <Typography sx={{ fontSize: TYPO.sm, color: textSecondary, mb: 1, lineHeight: 1.6 }}>
            Reachy should now be connected to{' '}
            <strong style={{ color: textPrimary }}>{configuredNetwork || 'your network'}</strong>.
          </Typography>
          <Typography sx={{ fontSize: TYPO.xs, color: textSecondary, mb: 1 }}>
            Searching for Reachy on the network...
          </Typography>
          {configuredNetwork && (
            <Typography
              sx={{ fontSize: TYPO.xs, color: ACCENT.main, fontWeight: FONT_WEIGHT.medium }}
            >
              Make sure your computer is connected to "{configuredNetwork}"
            </Typography>
          )}
        </>
      )}
    </Box>
  );
}
