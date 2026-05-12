import React, { useMemo, useEffect, useRef } from 'react';
import { Box, Typography } from '@mui/material';
import { ControllerProvider, useController } from './context/ControllerContext';
import { useControllerHandlers } from './hooks/useControllerHandlers';
import { useControllerSmoothing } from './hooks/useControllerSmoothing';
import { useControllerSync } from './hooks/useControllerSync';
import { useControllerAPI } from './hooks/useControllerAPI';
import { useControllerInput } from './hooks/useControllerInput';
import { logInfo } from '../../../utils/logging';
import { Joystick2D, VerticalSlider, SimpleSlider, CircularSlider } from './components';
import { EXTENDED_ROBOT_RANGES, INPUT_THRESHOLDS } from '../../../utils/inputConstants';
import { isHeadPoseZero, areAntennasZero, isZero } from '../../../utils/inputHelpers';
import { mapRobotToDisplay, mapDisplayToRobot } from '../../../utils/inputMappings';
import antennasIcon from '../../../assets/reachy-antennas-icon.svg';
import headIcon from '../../../assets/reachy-head-icon.svg';
import bodyIcon from '../../../assets/reachy-body-icon.svg';
import { FONT_WEIGHT, RADIUS, TYPO, useAppPalette } from '@styles';

function ControllerInner({
  onResetReady,
  onIsAtInitialPosition,
}: {
  onResetReady?: (resetFn: () => void) => void;
  onIsAtInitialPosition?: (atInitial: boolean) => void;
}): React.ReactElement {
  const { isDragging } = useController();
  const { sendCommand, forceSendCommand } = useControllerAPI();

  const wasDraggingRef = useRef<boolean>(false);
  useEffect(() => {
    if (isDragging && !wasDraggingRef.current) {
      logInfo('Manual control started');
    } else if (!isDragging && wasDraggingRef.current) {
      logInfo('Manual control ended');
    }
    wasDraggingRef.current = isDragging;
  }, [isDragging]);

  const {
    localValues,
    handleChange,
    handleBodyYawChange,
    handleAntennasChange,
    handleDragEnd,
    resetAllValues,
  } = useControllerHandlers({
    sendCommand: forceSendCommand as unknown as (
      headPose: Parameters<typeof sendCommand>[0],
      antennas: Parameters<typeof sendCommand>[1],
      bodyYaw: Parameters<typeof sendCommand>[2]
    ) => void,
  });

  const { smoothedValues } = useControllerSmoothing({ sendCommand });

  useControllerSync();

  useControllerInput();

  const isAtInitialPosition = useMemo<boolean>(() => {
    const { headPose, antennas, bodyYaw } = localValues;
    const tolerance = INPUT_THRESHOLDS.INITIAL_POSITION;
    return (
      isHeadPoseZero(headPose, tolerance) &&
      areAntennasZero(antennas, tolerance) &&
      isZero(bodyYaw, tolerance)
    );
  }, [localValues]);

  useEffect(() => {
    onResetReady?.(resetAllValues);
  }, [onResetReady, resetAllValues]);

  useEffect(() => {
    onIsAtInitialPosition?.(isAtInitialPosition);
  }, [onIsAtInitialPosition, isAtInitialPosition]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, width: '100%', flex: 1 }}>
      {/* ANTENNAS */}
      <SectionTitle icon={antennasIcon} label="Antennas" />
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
        <ControlCard>
          <CircularSlider
            label="Left"
            value={localValues.antennas?.[0] || 0}
            smoothedValue={smoothedValues?.antennas?.[0]}
            onChange={(v, continuous) => handleAntennasChange('left', v, continuous)}
            min={-Math.PI}
            max={Math.PI}
            unit="rad"
          />
        </ControlCard>
        <ControlCard alignRight>
          <CircularSlider
            label="Right"
            value={localValues.antennas?.[1] || 0}
            smoothedValue={smoothedValues?.antennas?.[1]}
            onChange={(v, continuous) => handleAntennasChange('right', v, continuous)}
            min={-Math.PI}
            max={Math.PI}
            unit="rad"
            alignRight
          />
        </ControlCard>
      </Box>

      {/* HEAD */}
      <SectionTitle icon={headIcon} label="Head" />
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
        {/* Position X/Y/Z */}
        <ControlCard padding={1}>
          <Box sx={{ display: 'flex', gap: 0, alignItems: 'stretch' }}>
            <Box sx={{ flex: '1 1 auto', display: 'flex', alignItems: 'center' }}>
              <Joystick2D
                label="Position X/Y"
                valueX={mapRobotToDisplay(localValues.headPose.y, 'positionY')}
                valueY={mapRobotToDisplay(localValues.headPose.x, 'positionX')}
                smoothedValueX={
                  smoothedValues?.headPose?.y != null
                    ? mapRobotToDisplay(smoothedValues.headPose.y, 'positionY')
                    : undefined
                }
                smoothedValueY={
                  smoothedValues?.headPose?.x != null
                    ? mapRobotToDisplay(smoothedValues.headPose.x, 'positionX')
                    : undefined
                }
                onChange={(x, y, continuous) => {
                  const robotY = mapDisplayToRobot(x, 'positionY');
                  const robotX = mapDisplayToRobot(y, 'positionX');
                  handleChange({ x: robotX, y: robotY }, continuous);
                }}
                onDragEnd={handleDragEnd}
                minX={EXTENDED_ROBOT_RANGES.POSITION.min}
                maxX={EXTENDED_ROBOT_RANGES.POSITION.max}
                minY={EXTENDED_ROBOT_RANGES.POSITION.min}
                maxY={EXTENDED_ROBOT_RANGES.POSITION.max}
                size={120}
              />
            </Box>
            <Box sx={{ flex: '0 0 auto', display: 'flex', alignItems: 'center', px: 2.5 }}>
              <VerticalSlider
                label="Position Z"
                value={localValues.headPose.z}
                smoothedValue={smoothedValues?.headPose?.z}
                onChange={(z, continuous) => handleChange({ z }, continuous)}
                min={-0.05}
                max={0.05}
                unit="m"
                centered
                height={120}
              />
            </Box>
          </Box>
        </ControlCard>

        {/* Pitch/Yaw */}
        <ControlCard padding={1}>
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <Joystick2D
              label="Pitch / Yaw"
              valueX={mapRobotToDisplay(localValues.headPose.yaw, 'yaw')}
              valueY={mapRobotToDisplay(localValues.headPose.pitch, 'pitch')}
              smoothedValueX={
                smoothedValues?.headPose?.yaw != null
                  ? mapRobotToDisplay(smoothedValues.headPose.yaw, 'yaw')
                  : undefined
              }
              smoothedValueY={
                smoothedValues?.headPose?.pitch != null
                  ? mapRobotToDisplay(smoothedValues.headPose.pitch, 'pitch')
                  : undefined
              }
              onChange={(yaw, pitch, continuous) => {
                const robotYaw = mapDisplayToRobot(yaw, 'yaw');
                const robotPitch = mapDisplayToRobot(pitch, 'pitch');
                handleChange({ yaw: robotYaw, pitch: robotPitch }, continuous);
              }}
              onDragEnd={handleDragEnd}
              minX={EXTENDED_ROBOT_RANGES.YAW.min}
              maxX={EXTENDED_ROBOT_RANGES.YAW.max}
              minY={EXTENDED_ROBOT_RANGES.PITCH.min}
              maxY={EXTENDED_ROBOT_RANGES.PITCH.max}
              size={120}
              labelAlign="right"
            />
          </Box>
        </ControlCard>
      </Box>

      {/* Roll */}
      <ControlCard>
        <SimpleSlider
          label="Roll"
          value={localValues.headPose.roll}
          smoothedValue={smoothedValues?.headPose?.roll}
          onChange={(roll, continuous) => handleChange({ roll }, continuous)}
          min={-0.5}
          max={0.5}
          showRollVisualization
        />
      </ControlCard>

      {/* BODY */}
      <SectionTitle icon={bodyIcon} label="Body" />
      <ControlCard>
        <CircularSlider
          label="Yaw"
          value={localValues.bodyYaw}
          smoothedValue={smoothedValues?.bodyYaw}
          onChange={(v, continuous) => handleBodyYawChange(v, continuous)}
          min={(-160 * Math.PI) / 180}
          max={(160 * Math.PI) / 180}
          unit="rad"
          inverted
          reverse
        />
      </ControlCard>
    </Box>
  );
}

interface ControllerProps {
  isActive: boolean;
  /** @deprecated Theme is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  onResetReady?: (resetFn: () => void) => void;
  onIsAtInitialPosition?: (atInitial: boolean) => void;
}

export default function Controller({
  isActive,
  onResetReady,
  onIsAtInitialPosition,
}: ControllerProps): React.ReactElement | null {
  if (!isActive) return null;

  return (
    <ControllerProvider isActive={isActive}>
      <ControllerInner onResetReady={onResetReady} onIsAtInitialPosition={onIsAtInitialPosition} />
    </ControllerProvider>
  );
}

// =============================================================================
// UI Components (extracted for readability)
// =============================================================================

function SectionTitle({ icon, label }: { icon: string; label: string }): React.ReactElement {
  const palette = useAppPalette();
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: -0.5 }}>
      <Box
        component="img"
        src={icon}
        alt={label}
        sx={{
          width: 20,
          height: 20,
          filter: palette.isDark ? 'brightness(0) invert(1)' : 'brightness(0) invert(0)',
          opacity: palette.isDark ? 0.7 : 0.6,
        }}
      />
      <Typography
        sx={{
          fontSize: TYPO.xs,
          fontWeight: FONT_WEIGHT.bold,
          color: palette.textSecondary,
          letterSpacing: '0.5px',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </Typography>
    </Box>
  );
}

function ControlCard({
  children,
  alignRight = false,
  padding = 0.5,
}: {
  children: React.ReactNode;
  alignRight?: boolean;
  padding?: number;
}): React.ReactElement {
  const palette = useAppPalette();
  return (
    <Box
      sx={{
        px: 1,
        py: padding,
        borderRadius: RADIUS.md,
        // TODO(style-migration): light-mode uses pure #ffffff here while palette.surfaceCard is 0.95 alpha.
        bgcolor: palette.isDark ? 'rgba(26, 26, 26, 0.8)' : '#ffffff',
        border: `1px solid ${palette.border}`,
        ...(alignRight && {
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-end',
          width: '100%',
        }),
      }}
    >
      {children}
    </Box>
  );
}
