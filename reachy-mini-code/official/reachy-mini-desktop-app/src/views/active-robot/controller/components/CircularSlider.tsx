import React, { useMemo, memo } from 'react';
import { Box, Typography, Slider } from '@mui/material';
import {
  ACCENT,
  FONT_WEIGHT,
  RADIUS,
  TYPO,
  accentAlpha,
  blackAlpha,
  whiteAlpha,
} from '@styles/tokens';
import { useAppPalette } from '@styles';

interface CircularSliderProps {
  label: string;
  value: number;
  onChange: (value: number, isDragging: boolean) => void;
  min?: number;
  max?: number;
  unit?: string;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  disabled?: boolean;
  inverted?: boolean;
  reverse?: boolean;
  alignRight?: boolean;
  smoothedValue?: number | null;
}

const CircularSlider = memo(function CircularSlider({
  label,
  value,
  onChange,
  min = -Math.PI,
  max = Math.PI,
  unit = 'rad',
  disabled = false,
  inverted = false,
  reverse = false,
  alignRight = false,
  smoothedValue,
}: CircularSliderProps): React.ReactElement {
  const palette = useAppPalette();
  const ARC_START = 0.01;
  const ARC_END = 0.74;
  const ARC_SPAN = ARC_END - ARC_START;
  const ARC_DEGREES = 270;

  const radius = 18;
  const border = 5;
  const circleRadius = radius - border / 2;
  const circumference = 2 * Math.PI * circleRadius;
  const strokeWidth = border;
  const innerStrokeWidth = border / 1.1;

  const convertToInternalRange = (val: number): number => {
    const normalized = (val - min) / (max - min);
    return ARC_START + normalized * ARC_SPAN;
  };

  const svgCalculations = useMemo(() => {
    const internalValue = convertToInternalRange(value);

    const effectiveInternalValue = reverse ? ARC_END - (internalValue - ARC_START) : internalValue;

    const strokeDashoffset = circumference * (1 - effectiveInternalValue);
    const totalStrokeDashoffset = circumference * (1 - ARC_END);

    const svgRotation = inverted ? -45 : 135;

    const progressAngle = reverse
      ? ARC_DEGREES - ((internalValue - ARC_START) / ARC_SPAN) * ARC_DEGREES
      : ((internalValue - ARC_START) / ARC_SPAN) * ARC_DEGREES;

    let ghostInternalValue: number | null = null;
    let ghostProgressAngle: number | null = null;
    if (smoothedValue !== undefined && smoothedValue !== null) {
      ghostInternalValue = convertToInternalRange(smoothedValue);
      const effectiveGhostInternalValue = reverse
        ? ARC_END - (ghostInternalValue - ARC_START)
        : ghostInternalValue;
      ghostProgressAngle = reverse
        ? ARC_DEGREES - ((ghostInternalValue - ARC_START) / ARC_SPAN) * ARC_DEGREES
        : ((ghostInternalValue - ARC_START) / ARC_SPAN) * ARC_DEGREES;
    }

    return {
      internalValue,
      effectiveInternalValue,
      strokeDashoffset,
      totalStrokeDashoffset,
      svgRotation,
      progressAngle,
      ghostProgressAngle,
    };
  }, [value, min, max, inverted, reverse, circumference, smoothedValue]);

  const displayValue =
    typeof value === 'number'
      ? value.toFixed(unit === 'deg' ? 1 : 3)
      : unit === 'deg'
        ? '0.0'
        : '0.000';

  const trackBgStroke = palette.isDark ? whiteAlpha(0.04) : blackAlpha(0.04);
  const trackBgStrokeMid = palette.isDark ? whiteAlpha(0.06) : blackAlpha(0.06);
  const trackBgStrokeHalo = palette.isDark ? whiteAlpha(0.05) : blackAlpha(0.05);
  const progressStroke = palette.isDark ? whiteAlpha(0.5) : blackAlpha(0.5);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: alignRight ? 'stretch' : 'center',
        gap: 0.5,
        p: 0.75,
        borderRadius: '0px',
        bgcolor: 'transparent',
        border: 'none',
        opacity: disabled ? 0.5 : 1,
        pointerEvents: disabled ? 'none' : 'auto',
        width: '100%',
        boxSizing: 'border-box',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          width: alignRight ? 'auto' : '100%',
          mb: 0.5,
          justifyContent: alignRight ? 'flex-end' : 'flex-start',
          flexDirection: alignRight ? 'row-reverse' : 'row',
          boxSizing: 'border-box',
          ml: alignRight ? 'auto' : 0,
        }}
      >
        {alignRight ? (
          <>
            <Typography
              sx={{
                fontSize: TYPO.micro,
                fontFamily: 'monospace',
                fontWeight: FONT_WEIGHT.medium,
                color: palette.textFaint,
                letterSpacing: '0.02em',
                textAlign: 'right',
              }}
            >
              {displayValue}
              {unit === 'deg' ? '°' : ` ${unit}`}
            </Typography>
            <Typography
              sx={{
                fontSize: TYPO.tiny,
                fontWeight: FONT_WEIGHT.bold,
                color: palette.textPrimary,
                letterSpacing: '-0.2px',
                textAlign: 'right',
              }}
            >
              {label}
            </Typography>
          </>
        ) : (
          <>
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
          </>
        )}
      </Box>

      <Box
        sx={{
          display: 'flex',
          flexDirection: alignRight ? 'row-reverse' : 'row',
          alignItems: 'center',
          gap: 1.5,
          width: '100%',
        }}
      >
        <Box
          sx={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <svg
            viewBox={`0 0 ${radius * 2} ${radius * 2}`}
            style={{
              transform: `rotate(${svgCalculations.svgRotation}deg)`,
              width: radius * 2,
              height: radius * 2,
              pointerEvents: 'none',
            }}
          >
            <defs>
              <filter
                id={`dropshadow-${label}`}
                filterUnits="userSpaceOnUse"
                colorInterpolationFilters="sRGB"
              >
                <feComponentTransfer in="SourceAlpha">
                  <feFuncR type="discrete" tableValues="0.3" />
                  <feFuncG type="discrete" tableValues="0.3" />
                  <feFuncB type="discrete" tableValues="0.3" />
                </feComponentTransfer>
                <feGaussianBlur stdDeviation="1.5" />
                <feOffset dx="1.5" dy="1" result="shadow" />
                <feComposite in="SourceGraphic" in2="shadow" operator="over" />
              </filter>
            </defs>

            <circle
              stroke={trackBgStroke}
              strokeLinecap="round"
              fill="none"
              strokeWidth={strokeWidth}
              strokeDashoffset={svgCalculations.totalStrokeDashoffset}
              strokeDasharray={circumference}
              style={{
                filter: `url(#dropshadow-${label})`,
              }}
              r={circleRadius}
              cx={radius}
              cy={radius}
            />

            <circle
              stroke={trackBgStrokeMid}
              strokeLinecap="round"
              fill="none"
              strokeWidth={strokeWidth}
              strokeDashoffset={svgCalculations.totalStrokeDashoffset}
              strokeDasharray={circumference}
              r={circleRadius}
              cx={radius}
              cy={radius}
            />

            <circle
              stroke={trackBgStrokeHalo}
              strokeLinecap="round"
              fill="none"
              strokeWidth={1}
              strokeDashoffset={svgCalculations.totalStrokeDashoffset}
              strokeDasharray={circumference}
              r={circleRadius + strokeWidth / 2 + 0.5}
              cx={radius}
              cy={radius}
            />

            <circle
              stroke={progressStroke}
              strokeLinecap="round"
              fill="none"
              strokeWidth={innerStrokeWidth}
              strokeDashoffset={svgCalculations.strokeDashoffset}
              strokeDasharray={circumference}
              r={circleRadius}
              cx={radius}
              cy={radius}
            />
          </svg>
        </Box>

        <Box
          sx={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
          }}
        >
          {smoothedValue !== undefined && smoothedValue !== null && (
            <Box
              sx={{
                position: 'absolute',
                left: `${((smoothedValue - min) / (max - min)) * 100}%`,
                top: '50%',
                transform: 'translate(-50%, -50%)',
                width: 12,
                height: 12,
                borderRadius: RADIUS.circle,
                bgcolor: accentAlpha(0.2),
                border: `1.5px solid ${accentAlpha(0.5)}`,
                zIndex: 1,
                pointerEvents: 'none',
                transition: 'left 0.05s linear',
              }}
            />
          )}
          <Slider
            orientation="horizontal"
            value={value}
            onChange={(_e, newValue) => onChange(newValue as number, true)}
            onChangeCommitted={(_e, newValue) => onChange(newValue as number, false)}
            min={min}
            max={max}
            step={0.1}
            disabled={disabled}
            sx={{
              color: ACCENT.main,
              height: 3,
              position: 'relative',
              zIndex: 2,
              '& .MuiSlider-thumb': {
                width: 12,
                height: 12,
                boxShadow: `0 2px 6px ${accentAlpha(0.4)}`,
                '&:hover': {
                  boxShadow: `0 4px 12px ${accentAlpha(0.6)}`,
                  width: 14,
                  height: 14,
                },
                '&:active': {
                  boxShadow: `0 4px 12px ${accentAlpha(0.8)}`,
                },
              },
              '& .MuiSlider-track': {
                height: 3,
                border: 'none',
              },
              '& .MuiSlider-rail': {
                height: 3,
                opacity: palette.isDark ? 0.2 : 0.3,
              },
            }}
          />
        </Box>
      </Box>
    </Box>
  );
});

export default CircularSlider;
