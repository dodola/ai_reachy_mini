import React from 'react';
import { Box, Typography } from '@mui/material';
import { doaToCssRotation } from '../../../hooks/audio/useDoA';
import { whiteAlpha, blackAlpha } from '@styles/tokens';
import { FONT_WEIGHT, RADIUS, useAppPalette } from '@styles';

export interface DoAIndicatorProps {
  angle: number | null;
  isTalking: boolean;
  isAvailable: boolean;
  /** @deprecated Theme is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
}

// TODO(style-migration): the "talking" active color uses MD green 500 rather than STATUS.success (#22c55e).
// Kept as-is to preserve the existing tone; add a dedicated palette token if we want to unify later.
const TALKING_COLOR = '#4CAF50';

/**
 * Direction of Arrival (DoA) Indicator
 *
 * Compact pill showing a directional arrow and "DoA" label.
 * Smooth transitions between idle (ghost) and active (green) states -
 * no conditional renders, no layout shifts.
 */
function DoAIndicator({
  angle,
  isTalking,
  isAvailable,
}: DoAIndicatorProps): React.ReactElement | null {
  const palette = useAppPalette();
  if (!isAvailable) {
    return null;
  }

  const rotation = doaToCssRotation(angle);

  const idleBg = palette.isDark ? whiteAlpha(0.04) : blackAlpha(0.03);
  const talkingBg = palette.isDark ? 'rgba(76, 175, 80, 0.15)' : 'rgba(76, 175, 80, 0.1)';
  const talkingBorder = palette.isDark ? 'rgba(76, 175, 80, 0.3)' : 'rgba(76, 175, 80, 0.2)';
  const idleArrowStroke = palette.textMuted;

  return (
    <Box
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '3px',
        px: 0.625,
        py: 0.25,
        borderRadius: RADIUS.sm,
        bgcolor: isTalking ? talkingBg : idleBg,
        border: `1px solid ${isTalking ? talkingBorder : 'transparent'}`,
        transition: 'background-color 0.35s ease, border-color 0.35s ease, opacity 0.35s ease',
        opacity: isTalking ? 1 : 0.5,
      }}
    >
      {/* Directional arrow - always rendered, animated via opacity + rotation */}
      <Box
        component="svg"
        viewBox="0 0 10 10"
        sx={{
          width: 9,
          height: 9,
          flexShrink: 0,
          transform: `rotate(${rotation}deg)`,
          transition: 'transform 0.2s ease-out, opacity 0.35s ease',
          opacity: isTalking ? 1 : 0.4,
        }}
      >
        <path
          d="M5 1.5 L5 8.5 M5 1.5 L2.5 4 M5 1.5 L7.5 4"
          fill="none"
          stroke={isTalking ? TALKING_COLOR : idleArrowStroke}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ transition: 'stroke 0.35s ease' }}
        />
      </Box>

      {/* Fixed-width container to prevent layout shift when text changes */}
      <Box sx={{ width: 36, overflow: 'hidden', position: 'relative', height: 9 }}>
        <Typography
          sx={{
            fontSize: 8,
            fontWeight: FONT_WEIGHT.semibold,
            color: isTalking ? TALKING_COLOR : palette.textFaint,
            textTransform: 'uppercase',
            letterSpacing: '0.4px',
            lineHeight: 1,
            transition: 'color 0.35s ease',
            userSelect: 'none',
            whiteSpace: 'nowrap',
            position: 'absolute',
            top: 0,
            left: 0,
          }}
        >
          {isTalking ? 'Talking' : 'Listening'}
        </Typography>
      </Box>
    </Box>
  );
}

export default React.memo(DoAIndicator);
