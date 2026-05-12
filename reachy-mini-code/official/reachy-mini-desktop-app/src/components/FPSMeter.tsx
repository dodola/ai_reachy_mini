import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography } from '@mui/material';
import { whiteAlpha, blackAlpha } from '@styles/tokens';
import { useAppPalette, TYPO, FONT_WEIGHT, RADIUS, BLUR } from '@styles';

export interface FPSMeterProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
}

/**
 * Simple FPS Meter component. Displays an FPS counter above the Reachy
 * status tag in the 3D viewer. Should be rendered inside `Viewer3D` with
 * `position: absolute`.
 */
export function FPSMeter(_props: FPSMeterProps = {}): React.ReactElement {
  const palette = useAppPalette();
  const isDark = palette.isDark;
  const [fps, setFps] = useState<number>(0);
  const frameCount = useRef<number>(0);
  const lastTime = useRef<number>(performance.now());
  const animationFrameId = useRef<number | null>(null);

  useEffect(() => {
    const measureFPS = (): void => {
      frameCount.current += 1;
      const currentTime = performance.now();
      const deltaTime = currentTime - lastTime.current;

      if (deltaTime >= 1000) {
        const currentFPS = Math.round((frameCount.current * 1000) / deltaTime);
        setFps(currentFPS);
        frameCount.current = 0;
        lastTime.current = currentTime;
      }

      animationFrameId.current = requestAnimationFrame(measureFPS);
    };

    animationFrameId.current = requestAnimationFrame(measureFPS);

    return () => {
      if (animationFrameId.current !== null) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, []);

  // TODO(style-migration): FPS pill uses a parametric 85% surface tint not
  // captured by surfaceCard (95%); keep an isDark branch.
  const bgColor = isDark ? 'rgba(26, 26, 26, 0.85)' : 'rgba(255, 255, 255, 0.85)';
  const borderColor = isDark ? whiteAlpha(0.1) : blackAlpha(0.1);
  const textColor = isDark ? whiteAlpha(0.6) : blackAlpha(0.5);

  return (
    <Box
      sx={{
        px: 1.25,
        py: 0.75,
        borderRadius: RADIUS.md,
        bgcolor: bgColor,
        border: `1px solid ${borderColor}`,
        backdropFilter: BLUR.md,
        pointerEvents: 'none',
      }}
    >
      <Typography
        sx={{
          fontSize: TYPO.micro,
          fontWeight: FONT_WEIGHT.medium,
          color: textColor,
          fontFamily: 'SF Mono, Monaco, Menlo, monospace',
          letterSpacing: '0.02em',
          lineHeight: 1,
        }}
      >
        {fps} FPS
      </Typography>
    </Box>
  );
}

/** Wrapper kept for backward compatibility. The inner component now reads the
 *  theme mode from `useAppPalette()` directly. */
export default function FPSMeterWrapper(): React.ReactElement {
  return <FPSMeter />;
}
