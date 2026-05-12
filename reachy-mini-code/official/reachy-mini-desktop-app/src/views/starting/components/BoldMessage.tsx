/**
 * BoldMessage - Text with bold emphasis
 *
 * Renders "text **bold** suffix" pattern used throughout scan messages.
 */

import React from 'react';
import { Box, Typography } from '@mui/material';
import { FONT_WEIGHT, useAppPalette } from '@styles';

export interface BoldMessageProps {
  text?: string;
  bold: string;
  suffix?: string;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  fontSize?: number;
}

function BoldMessage({ text, bold, suffix, fontSize = 14 }: BoldMessageProps) {
  const palette = useAppPalette();
  return (
    <Typography
      component="span"
      sx={{
        fontSize,
        fontWeight: FONT_WEIGHT.medium,
        color: palette.textPrimary,
        lineHeight: 1.5,
      }}
    >
      {text && `${text} `}
      <Box component="span" sx={{ fontWeight: FONT_WEIGHT.bold }}>
        {bold}
      </Box>
      {suffix && ` ${suffix}`}
    </Typography>
  );
}

export default React.memo(BoldMessage);
