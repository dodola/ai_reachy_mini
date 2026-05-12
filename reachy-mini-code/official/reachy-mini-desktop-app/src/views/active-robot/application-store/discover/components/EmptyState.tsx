import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import ReachyDetective from '@assets/reachy-detective.svg';
import { ACCENT, FONT_WEIGHT, RADIUS, TYPO } from '@styles/tokens';
import { useAppPalette } from '@styles';

interface EmptyStateProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
}

export default function EmptyState({
  searchQuery,
  setSearchQuery,
}: EmptyStateProps): React.ReactElement {
  const palette = useAppPalette();
  return (
    <Box
      sx={{
        py: 10,
        textAlign: 'center',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
      }}
    >
      <Box
        component="img"
        src={ReachyDetective}
        alt="Reachy Detective"
        sx={{
          width: 120,
          height: 'auto',
          opacity: palette.isDark ? 0.7 : 0.8,
          mb: 1,
        }}
      />

      {searchQuery ? (
        <>
          <Typography
            sx={{
              fontSize: TYPO.xl,
              fontWeight: FONT_WEIGHT.bold,
              color: palette.textSecondary,
              mb: 0.5,
            }}
          >
            Can&apos;t find what you&apos;re looking for?
          </Typography>
          <Typography
            sx={{
              fontSize: TYPO.md,
              color: palette.textMuted,
              mb: 2,
            }}
          >
            No apps found for &quot;{searchQuery}&quot;
          </Typography>
          <Button
            onClick={() => setSearchQuery('')}
            sx={{
              textTransform: 'none',
              fontSize: TYPO.md,
              fontWeight: FONT_WEIGHT.semibold,
              px: 3,
              py: 1,
              borderRadius: RADIUS.lg,
              bgcolor: 'transparent',
              color: ACCENT.main,
              border: `1px solid ${ACCENT.main}`,
              '&:hover': {
                bgcolor: palette.accentSurfaceHover,
                borderColor: ACCENT.main,
              },
            }}
          >
            Clear search
          </Button>
        </>
      ) : (
        <Typography
          sx={{
            fontSize: TYPO.xl,
            fontWeight: FONT_WEIGHT.bold,
            color: palette.textSecondary,
          }}
        >
          No apps available
        </Typography>
      )}
    </Box>
  );
}
