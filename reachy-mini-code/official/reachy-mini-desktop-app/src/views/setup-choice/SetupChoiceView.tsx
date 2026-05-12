import { Box, Typography } from '@mui/material';
import WifiOutlinedIcon from '@mui/icons-material/WifiOutlined';
import BluetoothIcon from '@mui/icons-material/Bluetooth';

import useAppStore from '../../store/useAppStore';
import FullscreenOverlayUntyped from '../../components/FullscreenOverlay';
import type React from 'react';
import {
  ACCENT,
  accentAlpha,
  DURATION,
  EASING,
  FONT_WEIGHT,
  RADIUS,
  TYPO,
  useAppPalette,
} from '@styles';

// TODO(ts): FullscreenOverlay lives outside this agent's migration scope; cast locally
// to a React.FC shape that matches the runtime call signature we use.
const FullscreenOverlay = FullscreenOverlayUntyped as unknown as React.FC<{
  open: boolean;
  onClose: () => void;
  children?: React.ReactNode;
  darkMode?: boolean;
  showCloseButton?: boolean;
  centered?: boolean;
  backdropBlur?: number;
  debugName?: string;
}>;

/**
 * SetupChoiceView - fullscreen overlay letting the user choose
 * between WiFi first-time setup and Bluetooth troubleshooting.
 */
export default function SetupChoiceView() {
  const palette = useAppPalette();
  const { setShowSetupChoice, setShowFirstTimeWifiSetup, setShowBluetoothSupportView } =
    useAppStore();

  const textPrimary = palette.textPrimary;
  // TODO(style-migration): the literal `#888` / `#666` pair has no exact
  // palette token; `textSecondary` is the closest semantic fit.
  const textSecondary = palette.textSecondary;
  const bgCard = palette.surfaceSubtle;
  const borderColor = palette.border;

  const handleWifi = () => {
    setShowSetupChoice(false);
    setShowFirstTimeWifiSetup(true);
  };

  const handleBluetooth = () => {
    setShowSetupChoice(false);
    setShowBluetoothSupportView(true);
  };

  const handleClose = () => {
    setShowSetupChoice(false);
  };

  return (
    <FullscreenOverlay
      open={true}
      onClose={handleClose}
      darkMode={palette.isDark}
      showCloseButton={true}
      centered={true}
      backdropBlur={40}
      debugName="SetupChoice"
    >
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          px: 3,
          py: 4,
          width: '100%',
          maxWidth: 480,
        }}
      >
        <Typography
          sx={{
            fontSize: 22,
            fontWeight: FONT_WEIGHT.bold,
            color: textPrimary,
            mb: 1,
            textAlign: 'center',
            letterSpacing: '-0.3px',
          }}
        >
          How would you like to proceed?
        </Typography>

        <Typography
          sx={{
            fontSize: TYPO.body,
            color: textSecondary,
            textAlign: 'center',
            mb: 3,
            lineHeight: 1.5,
          }}
        >
          Set up WiFi for the first time, or use Bluetooth to troubleshoot your robot.
        </Typography>

        {/* Cards container */}
        <Box sx={{ display: 'flex', gap: 2, width: '100%' }}>
          {/* WiFi Setup Card (primary) */}
          <Box
            onClick={handleWifi}
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 1,
              p: 3,
              borderRadius: RADIUS.xl,
              border: '2px solid',
              borderColor: ACCENT.main,
              bgcolor: palette.accentSurface,
              cursor: 'pointer',
              transition: `all ${DURATION.base}ms ${EASING.standard}`,
              '&:hover': {
                bgcolor: palette.accentSurfaceHover,
              },
            }}
          >
            <WifiOutlinedIcon sx={{ fontSize: 36, color: ACCENT.main }} />
            <Typography
              sx={{
                fontSize: 15,
                fontWeight: FONT_WEIGHT.semibold,
                color: textPrimary,
                textAlign: 'center',
              }}
            >
              WiFi Setup
            </Typography>
            <Typography
              sx={{
                fontSize: TYPO.xs,
                color: textSecondary,
                textAlign: 'center',
                lineHeight: 1.4,
              }}
            >
              First time connecting your Reachy to WiFi
            </Typography>
          </Box>

          {/* Bluetooth Card (secondary + Beta badge) */}
          <Box
            onClick={handleBluetooth}
            sx={{
              position: 'relative',
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 1,
              p: 3,
              borderRadius: RADIUS.xl,
              border: '1px solid',
              borderColor: borderColor,
              bgcolor: bgCard,
              cursor: 'pointer',
              transition: `all ${DURATION.base}ms ${EASING.standard}`,
              '&:hover': {
                borderColor: palette.borderStrong,
                // TODO(style-migration): hovered-card background doesn't
                // have a dedicated token yet; `surfaceCardHover` is close but
                // meant for full cards - using an accent-free overlay here.
                bgcolor: palette.surfaceSubtle,
              },
            }}
          >
            {/* Beta badge */}
            <Box
              sx={{
                position: 'absolute',
                top: 8,
                right: 8,
                px: 0.75,
                py: 0.25,
                borderRadius: RADIUS.xs,
                bgcolor: accentAlpha(palette.isDark ? 0.15 : 0.1),
                border: `1px solid ${palette.accentBorder}`,
              }}
            >
              <Typography
                sx={{
                  fontSize: 8,
                  fontWeight: FONT_WEIGHT.semibold,
                  color: ACCENT.main,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  lineHeight: 1,
                }}
              >
                beta
              </Typography>
            </Box>

            <BluetoothIcon sx={{ fontSize: 36, color: textSecondary }} />
            <Typography
              sx={{
                fontSize: 15,
                fontWeight: FONT_WEIGHT.semibold,
                color: textPrimary,
                textAlign: 'center',
              }}
            >
              Bluetooth
            </Typography>
            <Typography
              sx={{
                fontSize: TYPO.xs,
                color: textSecondary,
                textAlign: 'center',
                lineHeight: 1.4,
              }}
            >
              Troubleshoot or recover when WiFi is unavailable
            </Typography>
          </Box>
        </Box>
      </Box>
    </FullscreenOverlay>
  );
}
