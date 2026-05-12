import { Box, IconButton, Tooltip } from '@mui/material';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import { ACCENT, DURATION, accentAlpha, transition } from '@styles/tokens';
import { useAppPalette, TYPO, BLUR } from '@styles';

export interface SettingsButtonProps {
  onClick: () => void;
  disabled: boolean;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
}

export default function SettingsButton({
  onClick,
  disabled,
}: SettingsButtonProps): React.ReactElement {
  const palette = useAppPalette();

  return (
    <Box
      sx={{
        position: 'absolute',
        top: 12,
        right: 12,
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        zIndex: 10,
      }}
    >
      <Tooltip title="Settings" placement="top" arrow>
        <span>
          <IconButton
            onClick={onClick}
            size="small"
            disabled={disabled}
            sx={{
              width: 36,
              height: 36,
              transition: transition('all', DURATION.base),
              color: disabled ? palette.textMuted : ACCENT.main,
              bgcolor: palette.surfaceCard,
              border: '1px solid',
              borderColor: disabled ? palette.border : palette.accentBorderStrong,
              backdropFilter: BLUR.md,
              boxShadow: palette.shadowSm,
              opacity: disabled ? 0.4 : 1,
              '&:hover': {
                bgcolor: palette.isDark ? accentAlpha(0.15) : accentAlpha(0.1),
                borderColor: ACCENT.main,
                transform: disabled ? 'none' : 'scale(1.05)',
              },
              '&:active': {
                transform: disabled ? 'none' : 'scale(0.95)',
              },
              '&.Mui-disabled': {
                bgcolor: palette.isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.6)',
                color: palette.textMuted,
                borderColor: palette.border,
              },
            }}
          >
            <SettingsOutlinedIcon sx={{ fontSize: TYPO.xl }} />
          </IconButton>
        </span>
      </Tooltip>
    </Box>
  );
}
