import React, { useState } from 'react';
import { Box, Typography, Button, CircularProgress } from '@mui/material';
import type { SxProps, Theme } from '@mui/material/styles';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import SectionHeader from './SectionHeader';
import { buildApiUrl, fetchWithTimeout, DAEMON_CONFIG } from '../../../config/daemon';
import { useToast } from '../../../hooks/useToast';
import { useAppPalette, TYPO, RADIUS } from '@styles';

export interface SettingsCacheCardProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  cardStyle?: SxProps<Theme>;
  buttonStyle?: SxProps<Theme>;
  onResetAppsClick: () => void;
  isResettingApps: boolean;
}

export default function SettingsCacheCard({
  cardStyle,
  buttonStyle,
  onResetAppsClick,
  isResettingApps,
}: SettingsCacheCardProps): React.ReactElement {
  const palette = useAppPalette();
  const [isClearing, setIsClearing] = useState<boolean>(false);
  const { showToast } = useToast();

  const handleClearCache = async (): Promise<void> => {
    setIsClearing(true);

    try {
      const response = await fetchWithTimeout(
        buildApiUrl('/cache/clear-hf'),
        { method: 'POST' },
        DAEMON_CONFIG.TIMEOUTS.COMMAND,
        { label: 'Clear HF cache', silent: true }
      );

      if (response.ok) {
        const data = await response.json();
        showToast(data.message || 'Cache cleared successfully', 'success');
      } else {
        const error = await response.json();
        showToast(error.detail || 'Failed to clear cache', 'error');
      }
    } catch (err) {
      console.error('Failed to clear HuggingFace cache:', err);
      showToast('Connection error', 'error');
    } finally {
      setIsClearing(false);
    }
  };

  const textSecondary = palette.textSecondary;
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
      <SectionHeader title="Maintenance" icon={DeleteOutlineIcon} darkMode={palette.isDark} />

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        <Typography sx={{ fontSize: TYPO.sm, color: textSecondary, lineHeight: 1.5 }}>
          Free up disk space by clearing cached AI models.
        </Typography>

        <Button
          variant="outlined"
          onClick={handleClearCache}
          disabled={isClearing}
          startIcon={
            isClearing ? <CircularProgress size={16} color="inherit" /> : <DeleteOutlineIcon />
          }
          sx={dangerButtonStyle}
        >
          {isClearing ? 'Clearing...' : 'Clear HuggingFace Cache'}
        </Button>

        <Typography sx={{ fontSize: TYPO.sm, color: textSecondary, lineHeight: 1.5 }}>
          Uninstall all apps.
        </Typography>

        <Button
          variant="outlined"
          onClick={onResetAppsClick}
          disabled={isResettingApps}
          startIcon={
            isResettingApps ? <CircularProgress size={16} color="inherit" /> : <DeleteOutlineIcon />
          }
          sx={dangerButtonStyle}
        >
          {isResettingApps ? 'Resetting...' : 'Reset Apps Cache'}
        </Button>
      </Box>
    </Box>
  );
}
