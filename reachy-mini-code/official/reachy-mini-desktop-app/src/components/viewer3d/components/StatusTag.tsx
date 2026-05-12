import { Box, Typography } from '@mui/material';
import CircleIcon from '@mui/icons-material/Circle';
import { ROBOT_STATUS } from '../../../constants/robotStatus';
import type { BusyReason, RobotStatus } from '../../../types/robot';
import {
  useAppPalette,
  TYPO,
  FONT_WEIGHT,
  RADIUS,
  BLUR,
  STATUS,
  STATUS_TEXT,
  hexToRgba,
} from '@styles';

export interface StatusTagInfo {
  label: string;
  color: string;
  animated?: boolean;
}

export interface StatusTagProps {
  isActive: boolean;
  isOn: boolean | null;
  isMoving: boolean;
  robotStatus: RobotStatus | null;
  busyReason: BusyReason | null;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
}

const BUSY_LABELS: Record<BusyReason, StatusTagInfo> = {
  moving: { label: 'Moving', color: STATUS.busy },
  command: { label: 'Executing', color: STATUS.busy },
  'app-running': { label: 'App Running', color: STATUS.busy },
  installing: { label: 'Installing', color: STATUS.info },
};

/**
 * Status colors sit on top of a tinted border. The border alpha is slightly
 * stronger for busy/error states so the tag reads as "active" at a glance.
 */
const BORDER_BY_COLOR: Record<string, string> = {
  [STATUS.success]: hexToRgba(STATUS.success, 0.3),
  [STATUS.info]: hexToRgba(STATUS.info, 0.3),
  [STATUS.busy]: hexToRgba(STATUS.busy, 0.35),
  [STATUS.error]: hexToRgba(STATUS.error, 0.4),
  [STATUS_TEXT.neutral.dark]: hexToRgba(STATUS_TEXT.neutral.dark, 0.3),
  '#999': hexToRgba('#999999', 0.25),
};

function resolveStatus(props: StatusTagProps): StatusTagInfo {
  const { isActive, isOn, isMoving, robotStatus, busyReason } = props;

  if (robotStatus) {
    switch (robotStatus) {
      case ROBOT_STATUS.DISCONNECTED:
        return { label: 'Offline', color: '#999' };
      case ROBOT_STATUS.READY_TO_START:
        return { label: 'Ready to Start', color: STATUS.info };
      case ROBOT_STATUS.STARTING:
        return { label: 'Starting', color: STATUS.info, animated: true };
      case ROBOT_STATUS.SLEEPING:
        return { label: 'Sleeping', color: STATUS_TEXT.neutral.dark };
      case ROBOT_STATUS.READY:
        if (isOn === true) return { label: 'Ready', color: STATUS.success };
        if (isOn === false) return { label: 'Standby', color: STATUS_TEXT.neutral.dark };
        return { label: 'Connected', color: STATUS.info };
      case ROBOT_STATUS.BUSY: {
        const info = (busyReason && BUSY_LABELS[busyReason]) || {
          label: 'Busy',
          color: STATUS.busy,
        };
        return { ...info, animated: true };
      }
      case ROBOT_STATUS.STOPPING:
        return { label: 'Stopping', color: STATUS.error, animated: true };
      case ROBOT_STATUS.CRASHED:
        return { label: 'Crashed', color: STATUS.error };
      default:
        return { label: 'Unknown', color: '#999' };
    }
  }

  if (!isActive) return { label: 'Offline', color: '#999' };
  if (isMoving) return { label: 'Moving', color: STATUS.busy, animated: true };
  if (isOn === true) return { label: 'Ready', color: STATUS.success };
  if (isOn === false) return { label: 'Standby', color: STATUS_TEXT.neutral.dark };
  return { label: 'Connected', color: STATUS.info };
}

export default function StatusTag(props: StatusTagProps): React.ReactElement {
  const palette = useAppPalette();
  const status = resolveStatus(props);
  const borderColor = BORDER_BY_COLOR[status.color] ?? palette.divider;

  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: 12,
        left: 12,
        display: 'flex',
        alignItems: 'center',
        gap: 0.75,
        px: 1.5,
        py: 0.75,
        borderRadius: RADIUS.lg,
        bgcolor: palette.surfaceCard,
        border: `1.5px solid ${borderColor}`,
        backdropFilter: BLUR.md,
        transition: 'none',
        zIndex: 10,
      }}
    >
      <CircleIcon
        sx={{
          fontSize: 7,
          color: status.color,
          ...(status.animated && {
            animation: 'pulse-dot 1.5s ease-in-out infinite',
            '@keyframes pulse-dot': {
              '0%, 100%': { opacity: 1, transform: 'scale(1)' },
              '50%': { opacity: 0.6, transform: 'scale(1.3)' },
            },
          }),
        }}
      />
      <Typography
        sx={{
          fontSize: TYPO.xs,
          fontWeight: FONT_WEIGHT.semibold,
          color: status.color,
          letterSpacing: '0.2px',
        }}
      >
        {status.label}
      </Typography>
    </Box>
  );
}
