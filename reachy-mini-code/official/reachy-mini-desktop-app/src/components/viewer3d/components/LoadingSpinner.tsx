import { Box, CircularProgress } from '@mui/material';
import { DURATION, transition } from '@styles/tokens';
import { useAppPalette } from '@styles';

export interface LoadingSpinnerProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  visible: boolean;
  /**
   * Background color of the overlay while visible. Should match the host
   * viewer so the reveal is seamless. Falls back to the theme default.
   */
  backgroundColor?: string;
}

/**
 * Overlay spinner displayed while the 3D viewer waits for the first valid
 * robot pose to be applied. Absorbs the "flash" between mount and first
 * websocket frame so the user never sees the default URDF pose.
 *
 * The overlay is fully opaque while visible, then fades out smoothly once
 * the pose is ready.
 */
export default function LoadingSpinner({
  visible,
  backgroundColor,
}: LoadingSpinnerProps): React.ReactElement {
  const palette = useAppPalette();
  const bg = backgroundColor ?? (palette.isDark ? '#1a1a1a' : '#e0e0e0');

  return (
    <Box
      sx={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        pointerEvents: visible ? 'auto' : 'none',
        opacity: visible ? 1 : 0,
        transition: transition('opacity', DURATION.medium),
        bgcolor: bg,
        borderRadius: 'inherit',
        // Keep the z-index LOW and scoped. The overlay only needs to sit
        // above the Canvas sibling (which has no explicit z-index), not
        // compete globally. A high z-index (e.g. 20) could leak past weak
        // stacking contexts and paint over unrelated areas (like the main
        // camera viewport during a PIP swap).
        zIndex: 1,
      }}
    >
      <CircularProgress size={32} thickness={3} sx={{ color: palette.textMuted }} />
    </Box>
  );
}
