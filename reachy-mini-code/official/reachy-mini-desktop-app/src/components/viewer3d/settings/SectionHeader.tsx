import React from 'react';
import { Box, Typography } from '@mui/material';
import type { SvgIconComponent } from '@mui/icons-material';
import { useAppPalette, TYPO, FONT_WEIGHT } from '@styles';

export interface SectionHeaderProps {
  title: string;
  icon?: SvgIconComponent | null;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  action?: React.ReactNode;
}

export default function SectionHeader({
  title,
  icon: Icon,
  action,
}: SectionHeaderProps): React.ReactElement {
  const palette = useAppPalette();

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        mb: 2,
        pb: 1.5,
        borderBottom: `1px solid ${palette.border}`,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {Icon && <Icon sx={{ fontSize: TYPO.xl, color: palette.textSecondary }} />}
        <Typography
          sx={{
            fontSize: TYPO.md,
            fontWeight: FONT_WEIGHT.bold,
            color: palette.textPrimary,
            letterSpacing: '-0.2px',
          }}
        >
          {title}
        </Typography>
      </Box>
      {action}
    </Box>
  );
}
