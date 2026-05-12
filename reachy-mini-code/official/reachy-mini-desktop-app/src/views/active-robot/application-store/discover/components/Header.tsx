import React from 'react';
import { Box, Typography } from '@mui/material';
import hfLogo from '@assets/hf-logo.svg';
import Reachies from '@assets/reachies.svg';
import { FONT_WEIGHT, TYPO, useAppPalette } from '@styles';

interface HeaderProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
}

export default function Header(_props: HeaderProps): React.ReactElement {
  const palette = useAppPalette();
  return (
    <Box sx={{ mb: 0 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 0 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, flex: 1 }}>
          <Box
            component="img"
            src={Reachies}
            alt="Reachies"
            sx={{
              width: 100,
              mr: 3,
              height: 'auto',
              flexShrink: 0,
              mb: 2,
            }}
          />

          <Box sx={{ flex: 1 }}>
            <Typography
              sx={{
                fontSize: 32,
                fontWeight: FONT_WEIGHT.bold,
                color: palette.textPrimary,
                letterSpacing: '-0.5px',
                lineHeight: 1.2,
                mb: 0.5,
              }}
            >
              Discover Apps
            </Typography>
            <Typography
              sx={{
                fontSize: TYPO.md,
                color: palette.textMuted,
                fontWeight: FONT_WEIGHT.medium,
                letterSpacing: '0.1px',
                mb: 1,
              }}
            >
              Extend Reachy&apos;s capabilities
            </Typography>
            <Typography
              sx={{
                fontSize: TYPO.sm,
                color: palette.textSecondary,
                fontWeight: FONT_WEIGHT.regular,
                lineHeight: 1.6,
                maxWidth: '90%',
                mb: 1.5,
              }}
            >
              Install apps created by the{' '}
              <Box component="span" sx={{ fontWeight: FONT_WEIGHT.bold }}>
                community
              </Box>
              . Each app adds new{' '}
              <Box component="span" sx={{ fontWeight: FONT_WEIGHT.bold }}>
                behaviors, interactions, or features
              </Box>{' '}
              to your robot&#8212;from{' '}
              <Box component="span" sx={{ fontWeight: FONT_WEIGHT.bold }}>
                games and demos
              </Box>{' '}
              to advanced{' '}
              <Box component="span" sx={{ fontWeight: FONT_WEIGHT.bold }}>
                AI-powered applications
              </Box>
              .
            </Typography>

            <Typography
              component="div"
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 0.5,
                mt: 0.5,
                fontSize: TYPO.micro,
                color: palette.textMuted,
                fontWeight: FONT_WEIGHT.medium,
              }}
            >
              <Box
                component="span"
                sx={{
                  color: palette.textFaint,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Powered by
              </Box>
              <Box
                component="img"
                src={hfLogo}
                alt="Hugging Face"
                sx={{
                  height: 22,
                  width: 'auto',
                  opacity: 1,
                  display: 'inline-block',
                  verticalAlign: 'middle',
                }}
              />
              <Box component="span">Hugging Face</Box>
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
