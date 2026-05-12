import React, { useState, useEffect } from 'react';
import { Box, Typography } from '@mui/material';
import { getVersion } from '@utils/tauriCompat';
import { invoke } from '@tauri-apps/api/core';
import useAppStore from '../../store/useAppStore';
import { FONT_WEIGHT, RADIUS, TYPO, useAppPalette } from '@styles';

export interface RobotHeaderProps {
  daemonVersion?: string | null;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
}

interface SidecarSourceInfo {
  source?: string;
}

/**
 * Robot header with title, version and metadata
 * Apple style: minimalist, clean, spacious
 */
export default function RobotHeader({ daemonVersion }: RobotHeaderProps): React.ReactElement {
  const palette = useAppPalette();
  const { connectionMode } = useAppStore();
  const [appVersion, setAppVersion] = useState<string | null>('');
  const [sidecarBranch, setSidecarBranch] = useState<string | null>(null);

  useEffect(() => {
    getVersion()
      .then(setAppVersion)
      .catch(() => setAppVersion(null));
    invoke<SidecarSourceInfo>('get_sidecar_source')
      .then(info => {
        if (info?.source && info.source !== 'pypi') {
          setSidecarBranch(info.source);
        }
      })
      .catch(() => {});
  }, []);

  // Get connection type label
  const getConnectionLabel = (): string => {
    if (connectionMode === 'wifi') return 'WiFi';
    if (connectionMode === 'simulation') return 'Sim';
    return 'USB';
  };

  return (
    <Box
      sx={{
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        py: 1,
        mb: 1.5,
      }}
    >
      {/* Title with connection badge */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: -0.5 }}>
        <Typography
          sx={{
            fontSize: TYPO.xxl,
            fontWeight: FONT_WEIGHT.semibold,
            // TODO(style-migration): palette.textPrimary uses #333 in light; RobotHeader prefers Apple-like #1d1d1f.
            color: palette.isDark ? palette.textPrimary : '#1d1d1f',
            letterSpacing: '-0.4px',
          }}
        >
          Reachy Mini
        </Typography>
        {connectionMode && (
          <Typography
            component="span"
            sx={{
              fontSize: TYPO.tiny,
              fontWeight: FONT_WEIGHT.semibold,
              color: palette.textFaint,
              bgcolor: palette.surfaceSubtle,
              px: 0.75,
              py: 0.25,
              borderRadius: RADIUS.xs,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            {getConnectionLabel()}
          </Typography>
        )}
      </Box>

      {/* Version Subtitle - App + Daemon */}
      <Typography
        sx={{
          fontSize: TYPO.micro,
          fontWeight: FONT_WEIGHT.medium,
          color: palette.textFaint,
          fontFamily: 'SF Mono, Monaco, Menlo, monospace',
          mb: 0.75,
        }}
      >
        {appVersion ? `App v${appVersion}` : 'App ?'}
        <Box
          component="span"
          sx={{
            display: 'inline-block',
            width: 3,
            height: 3,
            borderRadius: RADIUS.circle,
            bgcolor: palette.textFaint,
            mx: 1,
            verticalAlign: 'middle',
          }}
        />
        {sidecarBranch
          ? `Daemon @${sidecarBranch}`
          : daemonVersion
            ? `Daemon v${daemonVersion}`
            : 'Daemon ?'}
      </Typography>
    </Box>
  );
}
