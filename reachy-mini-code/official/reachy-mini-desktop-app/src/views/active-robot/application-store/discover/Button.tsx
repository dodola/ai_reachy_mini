import React from 'react';
import StoreOutlinedIcon from '@mui/icons-material/StoreOutlined';
import PulseButton from '@components/PulseButton';
import { FONT_WEIGHT, TYPO, useAppPalette } from '@styles';

interface DiscoverAppsButtonProps {
  onClick: () => void;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  disabled?: boolean;
}

export default function DiscoverAppsButton({
  onClick,
  disabled = false,
}: DiscoverAppsButtonProps): React.ReactElement {
  const palette = useAppPalette();
  return (
    <PulseButton
      onClick={onClick}
      disabled={disabled}
      startIcon={<StoreOutlinedIcon sx={{ fontSize: TYPO.lg }} />}
      darkMode={palette.isDark}
      size="small"
      sx={{ fontSize: TYPO.sm, fontWeight: FONT_WEIGHT.bold, letterSpacing: '-0.2px' }}
    >
      Discover apps
    </PulseButton>
  );
}
