import React from 'react';
import { Box, Typography, IconButton, Button, CircularProgress, Switch } from '@mui/material';
import type { SxProps, Theme } from '@mui/material/styles';
import RefreshIcon from '@mui/icons-material/Refresh';
import SystemUpdateAltIcon from '@mui/icons-material/SystemUpdateAlt';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import NewReleasesOutlinedIcon from '@mui/icons-material/NewReleasesOutlined';
import SectionHeader from './SectionHeader';
import { STATUS } from '@styles/tokens';
import { useAppPalette, TYPO, FONT_WEIGHT, RADIUS } from '@styles';

export interface UpdateInfo {
  is_available?: boolean;
  current_version?: string;
  available_version?: string;
  [key: string]: unknown;
}

export interface SettingsUpdateCardProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  title?: string;
  updateInfo: UpdateInfo | null;
  isCheckingUpdate: boolean;
  isUpdating: boolean;
  preRelease: boolean;
  onPreReleaseChange: (value: boolean) => void;
  onCheckUpdate: () => void;
  onUpdateClick: () => void;
  cardStyle?: SxProps<Theme>;
  buttonStyle?: SxProps<Theme>;
  isOnline?: boolean;
}

export default function SettingsUpdateCard({
  title = 'System Update',
  updateInfo,
  isCheckingUpdate,
  isUpdating,
  preRelease,
  onPreReleaseChange,
  onCheckUpdate,
  onUpdateClick,
  cardStyle,
  buttonStyle,
  isOnline = true,
}: SettingsUpdateCardProps): React.ReactElement {
  const palette = useAppPalette();
  const textPrimary = palette.textPrimary;
  const textSecondary = palette.textSecondary;
  const textMuted = palette.textMuted;

  return (
    <Box sx={cardStyle}>
      <SectionHeader
        title={title}
        icon={SystemUpdateAltIcon}
        darkMode={palette.isDark}
        action={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box
              onClick={() => onPreReleaseChange(!preRelease)}
              sx={{
                display: 'flex',
                alignItems: 'center',
                cursor: 'pointer',
              }}
            >
              <Switch
                checked={preRelease}
                onChange={e => onPreReleaseChange(e.target.checked)}
                size="small"
                sx={{
                  transform: 'scale(0.75)',
                  '& .MuiSwitch-switchBase': {
                    '&.Mui-checked': {
                      color: 'primary.main',
                      '& + .MuiSwitch-track': {
                        bgcolor: 'primary.main',
                        opacity: 0.5,
                      },
                    },
                  },
                  '& .MuiSwitch-track': {
                    bgcolor: palette.isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)',
                  },
                }}
              />
              <Typography
                sx={{
                  fontSize: TYPO.tiny,
                  color: preRelease ? 'primary.main' : textMuted,
                  mr: 1,
                }}
              >
                Beta
              </Typography>
            </Box>

            <IconButton
              onClick={onCheckUpdate}
              size="small"
              disabled={isCheckingUpdate}
              sx={{
                color: textMuted,
                p: 0.5,
                '&:hover': { color: textSecondary },
              }}
            >
              <RefreshIcon
                sx={{
                  fontSize: TYPO.lg,
                  animation: isCheckingUpdate ? 'spin 1s linear infinite' : 'none',
                  '@keyframes spin': {
                    '0%': { transform: 'rotate(0deg)' },
                    '100%': { transform: 'rotate(360deg)' },
                  },
                }}
              />
            </IconButton>
          </Box>
        }
      />

      <Box sx={{ minHeight: 140, display: 'flex', flexDirection: 'column' }}>
        {isCheckingUpdate ? (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 1.5,
            }}
          >
            <CircularProgress size={24} color="primary" />
            <Typography sx={{ fontSize: TYPO.sm, color: textSecondary }}>
              Checking for updates...
            </Typography>
          </Box>
        ) : updateInfo ? (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              gap: 1.5,
            }}
          >
            {updateInfo.is_available ? (
              <>
                <NewReleasesOutlinedIcon sx={{ fontSize: 32, color: 'primary.main' }} />
                <Box>
                  <Typography
                    sx={{
                      fontSize: TYPO.md,
                      fontWeight: FONT_WEIGHT.semibold,
                      color: textPrimary,
                      mb: 0.5,
                    }}
                  >
                    Update available
                  </Typography>
                  <Typography
                    sx={{
                      fontSize: TYPO.body,
                      color: textSecondary,
                      fontFamily: 'monospace',
                    }}
                  >
                    {updateInfo.current_version} → {updateInfo.available_version}
                  </Typography>
                </Box>
                <Button
                  variant="outlined"
                  onClick={onUpdateClick}
                  disabled={isUpdating || !isOnline}
                  sx={{
                    ...buttonStyle,
                    fontSize: TYPO.body,
                    fontWeight: FONT_WEIGHT.semibold,
                    py: 1,
                    px: 4,
                    borderRadius: RADIUS.lg,
                  }}
                >
                  {isUpdating ? <CircularProgress size={18} color="primary" /> : 'Update Now'}
                </Button>
                {!isOnline && (
                  <Typography
                    sx={{
                      fontSize: TYPO.xs,
                      color: STATUS.warning,
                      fontStyle: 'italic',
                    }}
                  >
                    Requires internet connection
                  </Typography>
                )}
              </>
            ) : (
              <>
                <CheckCircleOutlineIcon sx={{ fontSize: 32, color: STATUS.success }} />
                <Box>
                  <Typography
                    sx={{
                      fontSize: TYPO.md,
                      fontWeight: FONT_WEIGHT.semibold,
                      color: textPrimary,
                      mb: 0.5,
                    }}
                  >
                    You're up to date
                  </Typography>
                  <Typography
                    sx={{
                      fontSize: TYPO.sm,
                      color: textMuted,
                      fontFamily: 'monospace',
                    }}
                  >
                    Version {updateInfo.current_version}
                  </Typography>
                </Box>
              </>
            )}
          </Box>
        ) : (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 1.5,
            }}
          >
            <Typography sx={{ fontSize: TYPO.sm, color: textSecondary }}>
              Check for available updates
            </Typography>
            <Button
              variant="outlined"
              onClick={onCheckUpdate}
              size="small"
              disabled={!isOnline}
              sx={{ ...buttonStyle, fontSize: TYPO.sm }}
            >
              Check now
            </Button>
            {!isOnline && (
              <Typography
                sx={{
                  fontSize: TYPO.xs,
                  color: STATUS.warning,
                  fontStyle: 'italic',
                  mt: 0.5,
                }}
              >
                Requires internet connection
              </Typography>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
}
