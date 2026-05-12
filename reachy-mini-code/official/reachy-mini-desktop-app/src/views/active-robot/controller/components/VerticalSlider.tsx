import React, { memo } from 'react';
import { Box, Typography, Slider } from '@mui/material';
import { ACCENT, FONT_WEIGHT, RADIUS, TYPO, accentAlpha, blackAlpha } from '@styles/tokens';
import { useAppPalette } from '@styles';

interface VerticalSliderProps {
  label: string;
  value: number;
  onChange: (value: number, isDragging: boolean) => void;
  min?: number;
  max?: number;
  unit?: string;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  disabled?: boolean;
  centered?: boolean;
  smoothedValue?: number | null;
  height?: number;
}

const VerticalSlider = memo(function VerticalSlider({
  label,
  value,
  onChange,
  min = -1,
  max = 1,
  unit = 'm',
  disabled = false,
  centered = false,
  smoothedValue,
  height = 135,
}: VerticalSliderProps): React.ReactElement {
  const palette = useAppPalette();
  const displayValue =
    typeof value === 'number'
      ? value.toFixed(unit === 'deg' ? 1 : 3)
      : unit === 'deg'
        ? '0.0'
        : '0.000';

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 0.5,
        px: 0.75,
        borderRadius: '0px',
        bgcolor: 'transparent',
        border: 'none',
        opacity: disabled ? 0.5 : 1,
        pointerEvents: disabled ? 'none' : 'auto',
      }}
    >
      {centered ? (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 0.25,
            mb: 0.5,
          }}
        >
          <Typography
            sx={{
              fontSize: TYPO.tiny,
              fontWeight: FONT_WEIGHT.bold,
              color: palette.textPrimary,
              letterSpacing: '-0.2px',
            }}
          >
            {label}
          </Typography>
          <Typography
            sx={{
              fontSize: TYPO.micro,
              fontFamily: 'monospace',
              fontWeight: FONT_WEIGHT.medium,
              color: palette.textFaint,
              letterSpacing: '0.02em',
            }}
          >
            {displayValue}
            {unit === 'deg' ? '°' : ` ${unit}`}
          </Typography>
        </Box>
      ) : (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%', mb: 0.5 }}>
          <Typography
            sx={{
              fontSize: TYPO.tiny,
              fontWeight: FONT_WEIGHT.bold,
              color: palette.textPrimary,
              letterSpacing: '-0.2px',
            }}
          >
            {label}
          </Typography>
          <Typography
            sx={{
              fontSize: TYPO.micro,
              fontFamily: 'monospace',
              fontWeight: FONT_WEIGHT.medium,
              color: palette.textFaint,
              letterSpacing: '0.02em',
            }}
          >
            {displayValue}
            {unit === 'deg' ? '°' : ` ${unit}`}
          </Typography>
        </Box>
      )}

      <Box
        sx={{
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'center',
          height: height,
          width: '100%',
          position: 'relative',
        }}
      >
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            py: 0,
            px: 0.5,
            position: 'relative',
          }}
        >
          {smoothedValue !== undefined && smoothedValue !== null && (
            <Box
              sx={{
                position: 'absolute',
                top: `${100 - ((smoothedValue - min) / (max - min)) * 100}%`,
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: 12,
                height: 12,
                borderRadius: RADIUS.circle,
                bgcolor: accentAlpha(0.2),
                border: `1.5px solid ${accentAlpha(0.5)}`,
                zIndex: 1,
                pointerEvents: 'none',
                transition: 'top 0.05s linear',
              }}
            />
          )}
          <Slider
            orientation="vertical"
            value={value}
            onChange={(_e, newValue) => onChange(newValue as number, true)}
            onChangeCommitted={(_e, newValue) => onChange(newValue as number, false)}
            min={min}
            max={max}
            step={0.001}
            disabled={disabled}
            sx={{
              color: ACCENT.main,
              width: 4,
              height: '100%',
              position: 'relative',
              zIndex: 2,
              '& .MuiSlider-thumb': {
                width: 12,
                height: 12,
                boxShadow: `0 2px 4px ${blackAlpha(0.2)}`,
                '&:hover': {
                  boxShadow: `0 2px 8px ${accentAlpha(0.4)}`,
                  width: 14,
                  height: 14,
                },
                '&:active': {
                  boxShadow: `0 2px 8px ${accentAlpha(0.6)}`,
                },
                '&::before': {
                  boxShadow: 'none',
                },
              },
              '& .MuiSlider-track': {
                width: 4,
                border: 'none',
              },
              '& .MuiSlider-rail': {
                width: 4,
                opacity: palette.isDark ? 0.2 : 0.3,
              },
            }}
          />
        </Box>
      </Box>
    </Box>
  );
});

export default VerticalSlider;
