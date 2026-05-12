import React from 'react';
import { Box, Snackbar } from '@mui/material';
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { STATUS, hexToRgba } from '@styles/tokens';
import { useAppPalette } from '@styles';

export type ToastSeverity = 'success' | 'error' | 'warning' | 'info';

export interface ToastState {
  open: boolean;
  message: React.ReactNode;
  severity: ToastSeverity;
}

export interface ToastProps {
  toast: ToastState;
  toastProgress: number;
  onClose: () => void;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  zIndex?: number;
}

interface ToastColors {
  background: string;
  border: string;
  text: string;
  progress: string;
}

/**
 * Premium Toast notification component.
 *
 * Features:
 * - Bottom-center positioning
 * - Glassmorphism design (backdrop blur + shadows)
 * - Progress bar animation
 * - Auto-dismiss after 3.5s
 * - Click to dismiss
 * - Dark/light mode support
 * - Success/Error/Info/Warning variants
 */
export default function Toast({
  toast,
  toastProgress,
  onClose,
  zIndex = 100001,
}: ToastProps): React.ReactElement {
  const palette = useAppPalette();

  const getIcon = (): React.ReactElement | null => {
    switch (toast.severity) {
      case 'success':
        return <CheckCircleOutlinedIcon sx={{ fontSize: 20, flexShrink: 0, color: 'inherit' }} />;
      case 'error':
        return <ErrorOutlineIcon sx={{ fontSize: 20, flexShrink: 0, color: 'inherit' }} />;
      case 'warning':
        return <WarningAmberIcon sx={{ fontSize: 20, flexShrink: 0, color: 'inherit' }} />;
      case 'info':
        return <InfoOutlinedIcon sx={{ fontSize: 20, flexShrink: 0, color: 'inherit' }} />;
      default:
        return null;
    }
  };

  const getColors = (): ToastColors => {
    switch (toast.severity) {
      case 'success':
        return {
          background: palette.statusSuccessSurface,
          border: palette.statusSuccessBorder,
          text: palette.statusSuccessText,
          progress: hexToRgba(STATUS.success, 0.8),
        };
      case 'error':
        return {
          background: palette.statusErrorSurface,
          border: palette.statusErrorBorder,
          text: palette.statusErrorText,
          progress: hexToRgba(STATUS.error, 0.8),
        };
      case 'warning':
        return {
          background: palette.statusWarningSurface,
          border: palette.statusWarningBorder,
          text: palette.statusWarningText,
          progress: hexToRgba(STATUS.warning, 0.8),
        };
      case 'info':
        return {
          background: palette.statusInfoSurface,
          border: palette.statusInfoBorder,
          text: palette.statusInfoText,
          progress: hexToRgba(STATUS.info, 0.8),
        };
      default:
        return {
          background: palette.statusNeutralSurface,
          border: palette.statusNeutralBorder,
          text: palette.statusNeutralText,
          progress: hexToRgba(STATUS.neutral, 0.8),
        };
    }
  };

  const colors = getColors();

  return (
    <Snackbar
      open={toast.open}
      autoHideDuration={3500}
      onClose={onClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      sx={{
        bottom: '24px !important',
        left: '50% !important',
        right: 'auto !important',
        transform: 'translateX(-50%) !important',
        display: 'flex !important',
        justifyContent: 'center !important',
        alignItems: 'center !important',
        width: '100%',
        zIndex,
        '& > *': {
          margin: '0 auto !important',
        },
      }}
    >
      <Box
        onClick={onClose}
        sx={{
          position: 'relative',
          overflow: 'hidden',
          borderRadius: '12px',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          boxShadow: `${palette.shadowLg}, ${palette.shadowSm}`,
          zIndex,
          cursor: 'pointer',
        }}
      >
        <Box
          sx={{
            position: 'relative',
            borderRadius: '12px',
            fontSize: 13,
            fontWeight: 500,
            letterSpacing: '-0.01em',
            background: colors.background,
            border: `1px solid ${colors.border}`,
            color: colors.text,
            minWidth: 240,
            maxWidth: 400,
            px: 3,
            py: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 1.5,
            overflow: 'hidden',
          }}
        >
          <Box
            sx={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              height: '2px',
              width: `${toastProgress}%`,
              background: colors.progress,
              transition: 'width 0.02s linear',
              borderRadius: '0 0 12px 12px',
            }}
          />

          {getIcon()}

          <Box sx={{ flex: 1, textAlign: 'center' }}>{toast.message}</Box>
        </Box>
      </Box>
    </Snackbar>
  );
}
