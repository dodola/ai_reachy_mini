import { Box, CircularProgress, Typography } from '@mui/material';
import reachySetupSvg from '../../../assets/reachy-how-to-create-app.svg';
import TipsCarousel from './TipsCarousel';
import { FONT_WEIGHT, TYPO, useAppPalette } from '@styles';

export interface BootstrapOverlayProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  /**
   * `null` = we haven't decided yet (briefly shows a lightweight spinner),
   * `true` = we're actively bootstrapping (shows the friendly explainer),
   * `false` should never reach this component (caller should render the scan instead).
   */
  isBootstrapping: boolean | null;
  /** Humanized label produced by `useBootstrapDetection`. */
  bootstrapMessage: string;
}

/**
 * Full-bleed overlay shown while the daemon is going through its first-run
 * Python environment setup. We deliberately swap the 3D viewer for a static
 * illustration here: bootstrap is slow and GPU-heavy, so rendering the URDF
 * on top of it would hurt without any benefit.
 */
export default function BootstrapOverlay({
  isBootstrapping,
  bootstrapMessage,
}: BootstrapOverlayProps): React.ReactElement {
  const palette = useAppPalette();
  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: '300px',
        height: '320px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
      }}
    >
      <Box
        component="img"
        src={reachySetupSvg}
        alt="Reachy Mini setting up"
        sx={{
          width: 140,
          height: 'auto',
          opacity: palette.isDark ? 0.9 : 1,
          mb: 1,
        }}
      />
      {isBootstrapping === true ? (
        <Box sx={{ textAlign: 'center' }}>
          <Typography
            sx={{
              fontSize: TYPO.xl,
              fontWeight: FONT_WEIGHT.bold,
              color: palette.textPrimary,
              mb: 0.5,
              letterSpacing: '-0.3px',
            }}
          >
            {bootstrapMessage || 'Preparing environment...'}
          </Typography>
          <Typography
            sx={{
              fontSize: TYPO.body,
              fontWeight: FONT_WEIGHT.regular,
              color: palette.textSecondary,
              mb: 0.5,
            }}
          >
            Grab a coffee, this will take a few minutes.
          </Typography>
          <Typography
            sx={{
              fontSize: TYPO.xs,
              fontWeight: FONT_WEIGHT.regular,
              color: palette.textFaint,
              fontStyle: 'italic',
            }}
          >
            This only happens once
          </Typography>
          <TipsCarousel interval={5000} />
        </Box>
      ) : (
        <CircularProgress size={24} thickness={3} sx={{ color: palette.textMuted }} />
      )}
    </Box>
  );
}
