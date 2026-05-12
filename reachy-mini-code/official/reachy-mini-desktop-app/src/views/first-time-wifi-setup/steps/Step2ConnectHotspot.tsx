import React from 'react';
import { Box, Typography, Button, CircularProgress } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import qrCodeImage from '../../../assets/reachy-mini-access-point-QR-code.png';
import type { WifiNetwork } from '../../../hooks/system/useLocalWifiScan';
import {
  ACCENT,
  accentAlpha,
  STATUS,
  blackAlpha,
  whiteAlpha,
  DURATION,
  EASING,
} from '@styles/tokens';
import { FONT_WEIGHT, RADIUS, TYPO, useAppPalette } from '@styles';

interface Step2ConnectHotspotProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  textPrimary: string;
  textSecondary: string;
  reachyHotspots: WifiNetwork[];
  isDaemonReachable: boolean;
  onOpenWifiSettings: () => void;
  isRetry?: boolean;
}

interface CredentialRowProps {
  label: string;
  value: string;
  field: string;
}

export default function Step2ConnectHotspot({
  textPrimary,
  textSecondary,
  reachyHotspots,
  isDaemonReachable,
  onOpenWifiSettings,
  isRetry = false,
}: Step2ConnectHotspotProps): React.ReactElement {
  const palette = useAppPalette();
  const isDark = palette.isDark;
  const hotspotName = reachyHotspots[0]?.ssid || 'reachy-mini-ap';
  const [copiedField, setCopiedField] = React.useState<string | null>(null);

  const handleCopy = async (text: string, field: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 1500);
    } catch (e) {
      console.error('Failed to copy:', e);
    }
  };

  const CredentialRow = ({ label, value, field }: CredentialRowProps): React.ReactElement => (
    <Box
      onClick={() => handleCopy(value, field)}
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        py: 0.75,
        px: 1.5,
        borderRadius: RADIUS.md,
        bgcolor: isDark ? whiteAlpha(0.04) : blackAlpha(0.03),
        cursor: 'pointer',
        transition: `all ${DURATION.fast}ms ${EASING.standard}`,
        '&:hover': {
          bgcolor: isDark ? whiteAlpha(0.08) : blackAlpha(0.06),
        },
      }}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 0.25 }}>
        <Typography
          sx={{
            fontSize: TYPO.micro,
            color: textSecondary,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}
        >
          {label}
        </Typography>
        <Typography
          sx={{
            fontSize: TYPO.body,
            fontWeight: FONT_WEIGHT.semibold,
            color: textPrimary,
            fontFamily: 'monospace',
          }}
        >
          {value}
        </Typography>
      </Box>
      {copiedField === field ? (
        <CheckIcon sx={{ fontSize: TYPO.md, color: STATUS.success }} />
      ) : (
        <ContentCopyIcon sx={{ fontSize: TYPO.md, color: textSecondary }} />
      )}
    </Box>
  );

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
      {isDaemonReachable ? (
        <>
          <Typography
            sx={{ fontSize: 15, fontWeight: FONT_WEIGHT.semibold, color: STATUS.success, mb: 1 }}
          >
            ✓ Connected to Reachy!
          </Typography>
          <Typography sx={{ fontSize: TYPO.sm, color: textSecondary }}>
            Moving to WiFi configuration...
          </Typography>
        </>
      ) : (
        <>
          {/* Show retry message if coming back from failed connection */}
          {isRetry && (
            <Box
              sx={{
                mb: 2,
                p: 1.5,
                borderRadius: RADIUS.md,
                bgcolor: palette.statusErrorSurface,
                border: `1px solid ${palette.statusErrorBorder}`,
              }}
            >
              <Typography
                sx={{
                  fontSize: TYPO.sm,
                  color: palette.statusErrorText,
                  lineHeight: 1.5,
                }}
              >
                Connection failed. Please reconnect to the Reachy hotspot to try again.
              </Typography>
            </Box>
          )}

          {/* QR Code + Credentials - Side by side */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 2,
              width: '100%',
              mb: 2.5,
            }}
          >
            {/* QR Code - 4/10 */}
            <Box
              sx={{
                width: '40%',
                flexShrink: 0,
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              <Box
                sx={{
                  // TODO(style-migration): the QR holder is always a white
                  // card (QR must read on any theme); keeping the raw `#fff`
                  // on purpose - not mapped to a palette surface.
                  bgcolor: '#fff',
                  p: 1,
                  borderRadius: RADIUS.lg,
                  width: 110,
                  height: 110,
                  boxShadow: isDark ? palette.shadowMd : palette.shadowSm,
                }}
              >
                <img
                  src={qrCodeImage}
                  alt="QR Code"
                  style={{ width: '100%', height: '100%', display: 'block', objectFit: 'contain' }}
                />
              </Box>
            </Box>

            {/* Credentials - 6/10 */}
            <Box sx={{ width: '60%', display: 'flex', flexDirection: 'column', gap: 0.75 }}>
              <Typography
                sx={{ fontSize: TYPO.tiny, color: textSecondary, mb: 0.5, textAlign: 'left' }}
              >
                Scan QR or connect manually:
              </Typography>
              <CredentialRow label="Network" value={hotspotName} field="network" />
              <CredentialRow label="Password" value="reachy-mini" field="password" />
            </Box>
          </Box>

          {/* Primary Button */}
          <Button
            variant="outlined"
            endIcon={<OpenInNewIcon sx={{ fontSize: TYPO.lg }} />}
            onClick={onOpenWifiSettings}
            fullWidth
            sx={{
              fontSize: TYPO.body,
              fontWeight: FONT_WEIGHT.semibold,
              textTransform: 'none',
              borderColor: ACCENT.main,
              color: ACCENT.main,
              py: 1,
              borderRadius: RADIUS.lg,
              mb: 2,
              '&:hover': {
                borderColor: ACCENT.dark,
                bgcolor: accentAlpha(0.08),
              },
            }}
          >
            Open WiFi Settings
          </Button>

          {/* Detection status */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <CircularProgress size={12} sx={{ color: ACCENT.main }} />
            <Typography sx={{ fontSize: TYPO.xs, color: textSecondary }}>
              Detecting connection - we'll auto-advance when connected
            </Typography>
          </Box>
        </>
      )}
    </Box>
  );
}
