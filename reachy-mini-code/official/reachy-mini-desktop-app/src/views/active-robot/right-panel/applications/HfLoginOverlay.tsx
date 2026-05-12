import React from 'react';
import { Box, Typography, Button, CircularProgress, Link } from '@mui/material';
import { ACCENT, DURATION, EASING, STATUS, accentAlpha } from '@styles/tokens';
import { FONT_WEIGHT, RADIUS, TYPO, transition, useAppPalette } from '@styles';
import hfLogo from '../../../../assets/hf-logo.svg';

export interface HfLoginOverlayProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  onLogin: () => void;
  onSkip?: () => void;
  isLoading?: boolean;
  isWaitingForAuth?: boolean;
  error?: string | null;
}

/**
 * Full-panel overlay shown when the user is not logged into Hugging Face.
 * Covers the entire RightPanel content with a blur backdrop and a centered login CTA.
 */
export default function HfLoginOverlay({
  onLogin,
  onSkip,
  isLoading,
  isWaitingForAuth,
  error,
}: HfLoginOverlayProps): React.ReactElement {
  const palette = useAppPalette();
  const busy = isLoading || isWaitingForAuth;

  return (
    <Box
      sx={{
        position: 'absolute',
        inset: 0,
        zIndex: 50,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        // TODO(style-migration): login scrim uses 0.85/0.88 alpha, not directly provided by palette.surface*.
        bgcolor: palette.isDark ? 'rgba(20, 20, 20, 0.85)' : 'rgba(248, 248, 250, 0.88)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        px: 4,
        gap: 2.5,
      }}
    >
      {/* HF Logo */}
      <Box
        component="img"
        src={hfLogo}
        alt="Hugging Face"
        sx={{ width: 56, height: 56, mb: 0.5 }}
      />

      {/* Title */}
      <Typography
        sx={{
          fontSize: TYPO.lg,
          fontWeight: FONT_WEIGHT.bold,
          color: palette.textPrimary,
          letterSpacing: '-0.2px',
          textAlign: 'center',
        }}
      >
        Sign in to Hugging Face
      </Typography>

      {/* Description */}
      <Typography
        sx={{
          fontSize: 12.5,
          color: palette.textSecondary,
          textAlign: 'center',
          lineHeight: 1.6,
          maxWidth: 280,
        }}
      >
        Connect your Hugging Face account to browse, install and manage applications on your Reachy
        Mini.
      </Typography>

      {/* Login button */}
      <Button
        disabled={busy}
        onClick={onLogin}
        startIcon={busy ? <CircularProgress size={14} sx={{ color: 'inherit' }} /> : null}
        sx={{
          mt: 0.5,
          py: 1.25,
          px: 4,
          fontSize: TYPO.body,
          fontWeight: FONT_WEIGHT.bold,
          textTransform: 'none',
          borderRadius: RADIUS.xl,
          color: '#fff',
          background: `linear-gradient(135deg, ${ACCENT.main}, ${ACCENT.dark})`,
          boxShadow: `0 2px 12px ${accentAlpha(0.25)}`,
          transition: transition('all', DURATION.base, EASING.standard),
          '&:hover': {
            // TODO(style-migration): custom accent-brighten gradient stops without palette equivalents.
            background: 'linear-gradient(135deg, #FFa520, #E89510)',
            boxShadow: `0 4px 16px ${accentAlpha(0.35)}`,
            transform: 'translateY(-1px)',
          },
          '&:disabled': {
            color: 'rgba(255,255,255,0.7)',
            background: accentAlpha(palette.isDark ? 0.3 : 0.4),
            boxShadow: 'none',
            transform: 'none',
          },
        }}
      >
        {isWaitingForAuth ? 'Waiting for login...' : isLoading ? 'Connecting...' : 'Sign in'}
      </Button>

      {/* Waiting hint */}
      {isWaitingForAuth && (
        <Typography
          sx={{
            fontSize: TYPO.xs,
            color: palette.textMuted,
            textAlign: 'center',
          }}
        >
          Complete the login in your browser
        </Typography>
      )}

      {/* Error */}
      {error && (
        <Typography
          sx={{
            fontSize: TYPO.xs,
            color: STATUS.error,
            textAlign: 'center',
            maxWidth: 280,
          }}
        >
          {error}
        </Typography>
      )}

      {/* Skip login link */}
      {!busy && onSkip && (
        <Link
          component="button"
          onClick={onSkip}
          underline="hover"
          sx={{
            mt: 0.5,
            fontSize: 11.5,
            color: palette.textMuted,
            cursor: 'pointer',
            transition: transition('color', DURATION.fast, EASING.standard),
            '&:hover': {
              color: palette.textSecondary,
            },
          }}
        >
          Continue without signing in
        </Link>
      )}
    </Box>
  );
}
