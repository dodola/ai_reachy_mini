import {
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Typography,
  CircularProgress,
  Box,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import type { SxProps, Theme } from '@mui/material/styles';
import { STATUS, whiteAlpha, blackAlpha } from '@styles/tokens';
import { useAppPalette, TYPO, scrollbarSx } from '@styles';

export interface NetworkSelectProps {
  value: string;
  onChange: (value: string) => void;
  networks?: string[];
  disabled?: boolean;
  onOpen?: (source?: string) => void;
  isLoading?: boolean;
  connectedNetwork?: string | null;
  showLabel?: boolean;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  zIndex?: number;
  sx?: SxProps<Theme>;
}

/**
 * NetworkSelect - Reusable WiFi network dropdown
 *
 * Used in:
 * - ChangeWifiOverlay (Settings)
 * - WiFiConfiguration (Setup flow)
 */
export default function NetworkSelect({
  value,
  onChange,
  networks = [],
  disabled = false,
  onOpen,
  isLoading = false,
  connectedNetwork = null,
  showLabel = false,
  zIndex = 10004,
  sx = {},
}: NetworkSelectProps) {
  const palette = useAppPalette();
  const scrollThumb = palette.isDark ? whiteAlpha(0.2) : blackAlpha(0.15);
  const scrollThumbHover = palette.isDark ? whiteAlpha(0.3) : blackAlpha(0.25);

  const selectContent = (
    <Select
      value={value}
      onChange={(e: SelectChangeEvent<string>) => onChange(e.target.value)}
      disabled={disabled}
      onOpen={() => {
        if (onOpen) onOpen('NetworkSelect-onOpen');
      }}
      size="small"
      fullWidth
      label={showLabel ? 'Network' : undefined}
      displayEmpty
      notched={showLabel}
      MenuProps={{
        sx: { zIndex },
        PaperProps: {
          sx: {
            maxHeight: 200,
            bgcolor: palette.surfaceCard,
            ...scrollbarSx(palette, {
              width: 6,
              radius: 3,
              thumb: scrollThumb,
              thumbHover: scrollThumbHover,
            }),
          },
        },
      }}
      renderValue={(val: unknown) => {
        if (!val) {
          return <span style={{ color: palette.textSecondary }}>Select a network</span>;
        }
        return val as string;
      }}
      sx={sx}
    >
      {isLoading && networks.length === 0 ? (
        <MenuItem value="" disabled sx={{ color: palette.textSecondary, fontSize: TYPO.sm }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CircularProgress size={14} thickness={3} sx={{ color: palette.textSecondary }} />
            <em>Scanning networks...</em>
          </Box>
        </MenuItem>
      ) : networks.length === 0 ? (
        <MenuItem value="" disabled sx={{ color: palette.textSecondary, fontSize: TYPO.sm }}>
          <em>No networks found</em>
        </MenuItem>
      ) : (
        networks.map((network, i) => {
          const isCurrentNetwork = Boolean(connectedNetwork && network === connectedNetwork);
          return (
            <MenuItem
              key={`${network}-${i}`}
              value={network}
              disabled={isCurrentNetwork}
              sx={{
                fontSize: TYPO.body,
                display: 'flex',
                justifyContent: 'space-between',
                '&.Mui-disabled': {
                  opacity: 1,
                  color: palette.textSecondary,
                },
              }}
            >
              {network}
              {isCurrentNetwork && (
                <Typography
                  component="span"
                  sx={{ fontSize: TYPO.tiny, color: STATUS.success, ml: 1 }}
                >
                  ✓ connected
                </Typography>
              )}
            </MenuItem>
          );
        })
      )}
    </Select>
  );

  if (showLabel) {
    return (
      <FormControl size="small" fullWidth>
        <InputLabel shrink>Network</InputLabel>
        {selectContent}
      </FormControl>
    );
  }

  return selectContent;
}
