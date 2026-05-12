import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import ReachyDetective from '@assets/reachy-detective.svg';
import { ACCENT, FONT_WEIGHT, RADIUS, TYPO } from '@styles/tokens';
import { useAppPalette } from '@styles';

interface FooterProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  onOpenCreateTutorial: () => void;
}

export default function Footer({ onOpenCreateTutorial }: FooterProps): React.ReactElement {
  const palette = useAppPalette();
  return (
    <Box
      sx={{
        width: '100%',
        mt: 4,
        pt: 0,
        pb: 12,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2.5,
      }}
    >
      <Box
        component="img"
        src={ReachyDetective}
        alt="Reachy Detective"
        sx={{
          width: 200,
          height: 'auto',
          opacity: palette.isDark ? 0.7 : 0.8,
        }}
      />

      <Typography
        sx={{
          fontSize: TYPO.xl,
          fontWeight: FONT_WEIGHT.bold,
          color: palette.textSecondary,
          textAlign: 'center',
        }}
      >
        Can&apos;t find what you&apos;re looking for?
      </Typography>
      <Button
        onClick={onOpenCreateTutorial}
        sx={{
          textTransform: 'none',
          fontSize: TYPO.md,
          fontWeight: FONT_WEIGHT.semibold,
          color: ACCENT.main,
          border: `1px solid ${ACCENT.main}`,
          borderRadius: RADIUS.lg,
          px: 3,
          py: 1,
          bgcolor: 'transparent',
          '&:hover': {
            bgcolor: palette.accentSurfaceHover,
            borderColor: ACCENT.main,
          },
        }}
      >
        Create your own app →
      </Button>
    </Box>
  );
}
