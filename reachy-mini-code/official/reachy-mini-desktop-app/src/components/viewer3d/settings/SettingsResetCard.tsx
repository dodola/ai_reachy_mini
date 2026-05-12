import React from 'react';
import { Box, Typography, Button, CircularProgress } from '@mui/material';
import type { SxProps, Theme } from '@mui/material/styles';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import DeleteForeverOutlinedIcon from '@mui/icons-material/DeleteForeverOutlined';
import SectionHeader from './SectionHeader';
import { useAppPalette, TYPO, RADIUS } from '@styles';

export interface SettingsResetCardProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  cardStyle?: SxProps<Theme>;
  buttonStyle?: SxProps<Theme>;
  onResetAppsVenv: () => void;
  isResettingAppsVenv: boolean;
  onResetPythonEnv: () => void;
  isResettingPythonEnv: boolean;
}

export default function SettingsResetCard({
  cardStyle,
  buttonStyle,
  onResetAppsVenv,
  isResettingAppsVenv,
  onResetPythonEnv,
  isResettingPythonEnv,
}: SettingsResetCardProps): React.ReactElement {
  const palette = useAppPalette();
  const textSecondary = palette.textSecondary;

  const isDisabled = isResettingAppsVenv || isResettingPythonEnv;

  const dangerButtonStyle = {
    ...buttonStyle,
    fontSize: TYPO.sm,
    py: 0.75,
    px: 2,
    borderRadius: RADIUS.md,
    color: palette.dangerText,
    borderColor: palette.dangerBorder,
    '&:hover': {
      borderColor: palette.dangerText,
      bgcolor: palette.dangerSurfaceHover,
    },
    '&:disabled': {
      borderColor: palette.border,
      color: palette.textDisabled,
    },
  };

  return (
    <Box sx={cardStyle}>
      <SectionHeader title="Environment" icon={RestartAltIcon} darkMode={palette.isDark} />

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        <Typography sx={{ fontSize: TYPO.sm, color: textSecondary, lineHeight: 1.5 }}>
          Reset the apps environment. Installed apps will need to be reinstalled.
        </Typography>

        <Button
          variant="outlined"
          onClick={onResetAppsVenv}
          disabled={isDisabled}
          startIcon={
            isResettingAppsVenv ? (
              <CircularProgress size={16} color="inherit" />
            ) : (
              <RestartAltIcon />
            )
          }
          sx={dangerButtonStyle}
        >
          {isResettingAppsVenv ? 'Resetting...' : 'Reset Apps Environment'}
        </Button>

        <Typography sx={{ fontSize: TYPO.sm, color: textSecondary, lineHeight: 1.5, mt: 1 }}>
          Delete all Python files and re-download everything. This may take a few minutes.
        </Typography>

        <Button
          variant="outlined"
          onClick={onResetPythonEnv}
          disabled={isDisabled}
          startIcon={
            isResettingPythonEnv ? (
              <CircularProgress size={16} color="inherit" />
            ) : (
              <DeleteForeverOutlinedIcon />
            )
          }
          sx={dangerButtonStyle}
        >
          {isResettingPythonEnv ? 'Resetting...' : 'Full Environment Reset'}
        </Button>
      </Box>
    </Box>
  );
}
