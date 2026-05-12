import React from 'react';
import { Box, Tooltip, CircularProgress } from '@mui/material';
import BedtimeOutlinedIcon from '@mui/icons-material/BedtimeOutlined';
import { ACCENT, DURATION, EASING, accentAlpha } from '@styles/tokens';
import { useAppPalette } from '@styles';
import { useWakeSleep } from '../hooks/useWakeSleep';
import { useActiveRobotContext } from '../context';

export interface SleepButtonProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
}

/**
 * Sleep Button Component
 *
 * Simple button to put the robot to sleep.
 * Only visible when robot is awake.
 *
 * Disabled when:
 * - Robot is transitioning
 * - Robot is busy
 * - Controller or Expressions view is active
 */
export default function SleepButton(_props: SleepButtonProps = {}): React.ReactElement {
  const palette = useAppPalette();
  const { isTransitioning, canToggle, goToSleep } = useWakeSleep();
  const { robotState } = useActiveRobotContext();
  const { rightPanelView } = robotState;

  // Disable when controller or expressions views are active
  const isControllerOrExpressionsActive =
    rightPanelView === 'controller' || rightPanelView === 'expressions';
  const isDisabled = !canToggle || isControllerOrExpressionsActive || isTransitioning;

  // Dynamic tooltip
  const getTooltipTitle = (): string => {
    if (isControllerOrExpressionsActive) {
      return `Close ${rightPanelView} first`;
    }
    if (isTransitioning) {
      return 'Transitioning...';
    }
    return 'Put robot to sleep';
  };

  return (
    <Tooltip title={getTooltipTitle()} arrow placement="bottom">
      <Box
        component="button"
        onClick={isDisabled ? undefined : goToSleep}
        sx={{
          position: 'absolute',
          top: 12,
          left: 56, // Right of power button
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 36,
          height: 36,
          bgcolor: palette.surfaceCard,
          border: `1px solid ${palette.isDark ? palette.borderStrong : palette.border}`,
          borderRadius: '50%',
          backdropFilter: 'blur(10px)',
          zIndex: 20,
          cursor: isDisabled ? 'not-allowed' : 'pointer',
          opacity: isDisabled ? 0.4 : 1,
          transition: `all ${DURATION.base}ms ${EASING.standard}`,
          boxShadow: palette.shadowSm,
          '&:hover': isDisabled
            ? {}
            : {
                bgcolor: palette.accentSurfaceHover,
                borderColor: ACCENT.main,
                transform: 'scale(1.05)',
              },
          '&:active': isDisabled
            ? {}
            : {
                transform: 'scale(0.95)',
              },
        }}
      >
        {isTransitioning ? (
          <CircularProgress size={16} thickness={3} sx={{ color: ACCENT.main }} />
        ) : (
          <BedtimeOutlinedIcon
            sx={{
              fontSize: 18,
              color: isDisabled ? accentAlpha(palette.isDark ? 0.3 : 0.4) : ACCENT.main,
            }}
          />
        )}
      </Box>
    </Tooltip>
  );
}
