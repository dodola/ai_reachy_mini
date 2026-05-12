import React from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import type { SxProps, Theme } from '@mui/material/styles';
import WifiIcon from '@mui/icons-material/Wifi';
import SectionHeader from './SectionHeader';
import { STATUS } from '@styles/tokens';
import { useAppPalette, TYPO, FONT_WEIGHT, RADIUS } from '@styles';

export interface WifiStatus {
  mode?: 'wlan' | 'hotspot' | 'disconnected' | string;
  connected_network?: string;
  known_networks?: string[];
  [key: string]: unknown;
}

export interface SettingsWifiCardProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  wifiStatus: WifiStatus | null;
  isLoadingWifi: boolean;
  onRefresh: () => void;
  onChangeNetwork: () => void;
  onClearAllNetworks: () => void;
  cardStyle?: SxProps<Theme>;
}

export default function SettingsWifiCard({
  wifiStatus,
  isLoadingWifi,
  onChangeNetwork,
  onClearAllNetworks,
  cardStyle,
}: SettingsWifiCardProps): React.ReactElement {
  const palette = useAppPalette();
  const textPrimary = palette.textPrimary;
  const textSecondary = palette.textSecondary;
  const textMuted = palette.textMuted;

  const isConnected = wifiStatus?.mode === 'wlan';
  const isHotspot = wifiStatus?.mode === 'hotspot';
  const isDisconnected = wifiStatus?.mode === 'disconnected';
  const knownNetworks = wifiStatus?.known_networks || [];

  return (
    <Box sx={{ ...cardStyle, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <SectionHeader
        title="WiFi Network"
        icon={WifiIcon}
        darkMode={palette.isDark}
        action={
          wifiStatus && (
            <Typography
              onClick={onChangeNetwork}
              sx={{
                fontSize: TYPO.xs,
                color: textMuted,
                textDecoration: 'underline',
                cursor: 'pointer',
                '&:hover': { color: textSecondary },
              }}
            >
              Change network
            </Typography>
          )
        }
      />

      <Box sx={{ minHeight: 140, display: 'flex', flexDirection: 'column' }}>
        {isLoadingWifi && !wifiStatus ? (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 1.5,
            }}
          >
            <CircularProgress size={24} color="primary" />
            <Typography sx={{ fontSize: TYPO.sm, color: textSecondary }}>
              Scanning networks...
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              gap: 1.5,
            }}
          >
            <Box>
              <Typography
                sx={{
                  fontSize: TYPO.md,
                  fontWeight: FONT_WEIGHT.semibold,
                  color: textPrimary,
                  mb: 0.5,
                }}
              >
                {isConnected
                  ? wifiStatus?.connected_network
                  : isHotspot
                    ? 'Hotspot mode'
                    : isDisconnected
                      ? 'Disconnected'
                      : 'Unknown'}
              </Typography>
              <Typography
                sx={{
                  fontSize: TYPO.sm,
                  color: isConnected ? STATUS.success : isHotspot ? STATUS.warning : textMuted,
                }}
              >
                {isConnected
                  ? 'Connected'
                  : isHotspot
                    ? 'Broadcasting network'
                    : 'Not connected to any network'}
              </Typography>
            </Box>

            {knownNetworks.length > 0 && (
              <Box sx={{ width: '100%', mt: 0.5 }}>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 1,
                    mb: 0.75,
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: TYPO.tiny,
                      fontWeight: FONT_WEIGHT.semibold,
                      color: textMuted,
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px',
                    }}
                  >
                    Saved ({knownNetworks.length})
                  </Typography>
                  <Typography sx={{ color: textMuted, fontSize: TYPO.tiny }}>•</Typography>
                  <Typography
                    onClick={onClearAllNetworks}
                    sx={{
                      fontSize: TYPO.tiny,
                      color: STATUS.error,
                      cursor: 'pointer',
                      '&:hover': { textDecoration: 'underline' },
                    }}
                  >
                    Clear all
                  </Typography>
                </Box>
                <Box
                  sx={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    justifyContent: 'center',
                    gap: 0.5,
                  }}
                >
                  {knownNetworks.map(network => {
                    const isActive = network === wifiStatus?.connected_network;
                    return (
                      <Box
                        key={network}
                        sx={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          py: 0.25,
                          px: 0.75,
                          borderRadius: RADIUS.sm,
                          bgcolor: isActive
                            ? palette.isDark
                              ? 'rgba(34, 197, 94, 0.15)'
                              : 'rgba(34, 197, 94, 0.1)'
                            : palette.surfaceSubtle,
                          border: isActive
                            ? '1px solid rgba(34, 197, 94, 0.3)'
                            : `1px solid ${palette.border}`,
                        }}
                      >
                        <Typography
                          sx={{
                            fontSize: TYPO.xs,
                            color: isActive ? STATUS.success : textSecondary,
                            fontWeight: isActive ? FONT_WEIGHT.semibold : FONT_WEIGHT.regular,
                            maxWidth: 100,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {network}
                        </Typography>
                      </Box>
                    );
                  })}
                </Box>
              </Box>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
}
