import { useEffect, useState } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import { getAppWindow } from '../../utils/windowUtils';
import { BLUR, FONT_WEIGHT, TYPO, useAppPalette } from '@styles';

type ShutdownStep = {
  /** Elapsed time (ms) since shutdown start when this step becomes current. */
  at: number;
  label: string;
};

// Timings mirror `stopDaemon` + `performGracefulShutdown` in
// `hooks/daemon/useDaemon.ts`:
//   - close apps / windows (~500ms)
//   - `goto_sleep` animation (~6000ms)
//   - disable motors (~300ms)
//   - daemon process stop + cleanup
// The final entries act as upper bounds: the view unmounts as soon as
// `isStopping` flips back to false, so overshooting is fine.
const SHUTDOWN_STEPS: readonly ShutdownStep[] = [
  { at: 0, label: 'Closing running applications' },
  { at: 500, label: 'Moving Reachy to rest position' },
  { at: 6500, label: 'Disabling motors' },
  { at: 7000, label: 'Shutting down daemon' },
];

/**
 * View displayed during daemon shutdown.
 *
 * Instead of a random tagline, we walk through the real phases of the
 * graceful shutdown so the user knows exactly what's happening.
 */
export default function ClosingView() {
  const appWindow = getAppWindow();
  const palette = useAppPalette();
  const [stepIndex, setStepIndex] = useState<number>(0);

  useEffect(() => {
    const timers = SHUTDOWN_STEPS.slice(1).map((step, idx) =>
      window.setTimeout(() => setStepIndex(idx + 1), step.at)
    );
    return () => {
      timers.forEach(t => window.clearTimeout(t));
    };
  }, []);

  const currentStep = SHUTDOWN_STEPS[stepIndex];

  return (
    <Box
      sx={{
        width: '100vw',
        height: '100vh',
        // TODO(style-migration): bespoke backdrop alphas don't map to a
        // single surface token; `surfaceCard` is the closest match.
        background: palette.surfaceCard,
        backdropFilter: BLUR.lg,
        WebkitBackdropFilter: BLUR.lg,
        overflow: 'hidden',
      }}
    >
      {/* Titlebar (drag zone only, no window controls) */}
      <Box
        onMouseDown={async (e: React.MouseEvent<HTMLDivElement>) => {
          e.preventDefault();
          try {
            await appWindow.startDragging();
          } catch (err) {
            console.error('Drag error:', err);
          }
        }}
        sx={{
          height: 44,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          cursor: 'move',
          userSelect: 'none',
        }}
      >
        <Box sx={{ width: 12, height: 12 }} />
        <Box sx={{ height: 20 }} />
        <Box sx={{ width: 20, height: 20 }} />
      </Box>

      {/* Body */}
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: 'calc(100% - 44px)',
          gap: 2.5,
          textAlign: 'center',
          px: 4,
        }}
      >
        <CircularProgress size={32} thickness={4} sx={{ color: palette.textMuted }} />

        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 0.75,
            minHeight: 44,
            justifyContent: 'flex-start',
          }}
        >
          <Typography
            sx={{
              fontSize: TYPO.body,
              fontWeight: FONT_WEIGHT.semibold,
              color: palette.textPrimary,
            }}
          >
            Putting Reachy to sleep
          </Typography>
          <Typography
            key={currentStep.label}
            sx={{
              fontSize: TYPO.sm,
              fontWeight: FONT_WEIGHT.regular,
              color: palette.textSecondary,
              opacity: 0,
              animation: 'closingStepFadeIn 240ms ease-out forwards',
              '@keyframes closingStepFadeIn': {
                '0%': { opacity: 0, transform: 'translateY(2px)' },
                '100%': { opacity: 1, transform: 'translateY(0)' },
              },
            }}
          >
            {currentStep.label}...
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
