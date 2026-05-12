import React, { type ErrorInfo, type ReactNode } from 'react';
import { Box, Typography, Button } from '@mui/material';
import { buildAppPalette, whiteAlpha, blackAlpha, TYPO, FONT_WEIGHT, RADIUS } from '@styles';

export interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Global error boundary that catches unhandled render errors and displays a
 * recovery UI instead of a blank white screen.
 *
 * Class component because React error boundaries require `componentDidCatch`
 * and `getDerivedStateFromError` (no hook equivalent). The fallback UI builds
 * the palette from `matchMedia` so we stay independent of the store, which
 * may itself be part of the crash.
 */
class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary] Uncaught render error:', error, info.componentStack);

    try {
      // Synchronous require keeps the boundary working even if telemetry fails.

      const { telemetry } = require('../utils/telemetry') as {
        telemetry: { appCrash: (props: Record<string, unknown>) => void };
      };
      telemetry.appCrash({
        error_type: 'react_render_crash',
        error_message: error?.message,
        stack: error?.stack?.slice(0, 500),
      });
    } catch {
      // Telemetry unavailable - swallow silently
    }
  }

  handleRecover = (): void => {
    this.setState({ hasError: false, error: null });
  };

  handleFullReset = (): void => {
    try {
      const useStore = require('../store/useStore').useStore as {
        getState: () => { resetAll: () => void };
      };
      useStore.getState().resetAll();
    } catch {
      // Store unavailable
    }
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    // The React tree crashed, so we can't safely call hooks here. Build the
    // palette manually from the OS theme preference.
    const isDark =
      typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches;
    const palette = buildAppPalette(Boolean(isDark));

    // TODO(style-migration): recovery screen background uses a specific
    // fallback shade (#fafafc / #1a1a1a) that doesn't match surfaceBg; keep as
    // isDark branches so the fallback stays visually distinctive.
    const recoveryBg = palette.isDark ? '#1a1a1a' : '#fafafc';
    const recoveryText = palette.isDark ? '#fff' : '#1a1a1a';

    return (
      <Box
        sx={{
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 3,
          bgcolor: recoveryBg,
          color: recoveryText,
          px: 4,
          textAlign: 'center',
        }}
      >
        <Typography variant="h5" fontWeight={FONT_WEIGHT.semibold}>
          Something went wrong
        </Typography>

        <Typography
          sx={{
            fontSize: TYPO.body,
            color: palette.isDark ? whiteAlpha(0.5) : blackAlpha(0.45),
            maxWidth: 420,
            lineHeight: 1.6,
          }}
        >
          An unexpected error occurred in the interface. The robot daemon is still running in the
          background.
        </Typography>

        {this.state.error && (
          <Box
            className="selectable-text"
            sx={{
              mt: 1,
              px: 2,
              py: 1.5,
              borderRadius: RADIUS.md,
              bgcolor: palette.isDark ? whiteAlpha(0.06) : blackAlpha(0.04),
              maxWidth: 500,
              overflow: 'auto',
            }}
          >
            <Typography
              sx={{
                fontFamily: 'monospace',
                fontSize: TYPO.xs,
                color: palette.isDark ? whiteAlpha(0.4) : blackAlpha(0.35),
                wordBreak: 'break-word',
                cursor: 'text',
              }}
            >
              {this.state.error.message}
            </Typography>
          </Box>
        )}

        <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
          <Button variant="contained" onClick={this.handleRecover}>
            Retry
          </Button>
          <Button variant="outlined" onClick={this.handleFullReset}>
            Reset &amp; Reconnect
          </Button>
        </Box>
      </Box>
    );
  }
}

export default ErrorBoundary;
