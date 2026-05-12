import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Box, Typography, Switch, CircularProgress } from '@mui/material';
import type { SxProps, Theme } from '@mui/material/styles';
import PowerSettingsNewIcon from '@mui/icons-material/PowerSettingsNew';
import { buildApiUrl, fetchWithTimeout, DAEMON_CONFIG } from '../../../config/daemon';
import SectionHeader from './SectionHeader';
import { DURATION, STATUS, blackAlpha, transition } from '@styles/tokens';
import { useAppPalette, TYPO, FONT_WEIGHT, RADIUS } from '@styles';

type DaemonStateKey = 'running' | 'starting' | 'stopping' | 'stopped' | 'not_initialized' | 'error';

const STATE_LABELS: Record<DaemonStateKey, string> = {
  running: 'Up and ready',
  starting: 'Waking up...',
  stopping: 'Going to sleep...',
  stopped: 'Stopped',
  not_initialized: 'Stopped',
  error: 'Error',
};

const STATE_COLORS: Record<DaemonStateKey, string> = {
  running: STATUS.success,
  starting: STATUS.warning,
  stopping: STATUS.warning,
  stopped: STATUS.neutral,
  not_initialized: STATUS.neutral,
  error: STATUS.error,
};

export interface SettingsDaemonCardProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  cardStyle?: SxProps<Theme>;
}

export default function SettingsDaemonCard({
  cardStyle,
}: SettingsDaemonCardProps): React.ReactElement {
  const palette = useAppPalette();
  const [daemonState, setDaemonState] = useState<string | null>(null);
  const [isToggling, setIsToggling] = useState<boolean>(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const textPrimary = palette.textPrimary;
  const textSecondary = palette.textSecondary;

  const isRunning = daemonState === 'running';
  const isTransitioning = daemonState === 'starting' || daemonState === 'stopping';
  const stateKey = daemonState as DaemonStateKey | null;
  const statusLabel = (stateKey && STATE_LABELS[stateKey]) || daemonState || 'Loading...';
  const statusColor = (stateKey && STATE_COLORS[stateKey]) || textSecondary;

  const fetchStatus = useCallback(async (): Promise<void> => {
    try {
      const response = await fetchWithTimeout(
        buildApiUrl('/api/daemon/status'),
        {},
        DAEMON_CONFIG.TIMEOUTS.COMMAND,
        { label: 'Daemon status', silent: true }
      );
      if (response.ok) {
        const data = await response.json();
        setDaemonState(data.state || null);
      }
    } catch {
      // Daemon unreachable
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    pollingRef.current = setInterval(fetchStatus, 2000);
    return () => {
      if (pollingRef.current !== null) {
        clearInterval(pollingRef.current);
      }
    };
  }, [fetchStatus]);

  const handleToggle = useCallback(async (): Promise<void> => {
    if (isToggling || isTransitioning) return;
    setIsToggling(true);

    try {
      if (isRunning) {
        await fetchWithTimeout(
          buildApiUrl('/api/daemon/stop?goto_sleep=true'),
          { method: 'POST' },
          DAEMON_CONFIG.TIMEOUTS.COMMAND,
          { label: 'Stop daemon', silent: true }
        );
      } else {
        await fetchWithTimeout(
          buildApiUrl('/api/daemon/start?wake_up=true'),
          { method: 'POST' },
          DAEMON_CONFIG.TIMEOUTS.COMMAND,
          { label: 'Start daemon', silent: true }
        );
      }
      for (let i = 0; i < 10; i++) {
        await new Promise<void>(r => setTimeout(r, 500));
        await fetchStatus();
      }
    } catch (err) {
      console.error('[Settings] Daemon toggle error:', err);
    } finally {
      setIsToggling(false);
    }
  }, [isRunning, isToggling, isTransitioning, fetchStatus]);

  return (
    <Box sx={cardStyle}>
      <SectionHeader title="Robot Control" icon={null} darkMode={palette.isDark} />

      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 1.5,
          borderRadius: RADIUS.xl,
          bgcolor: palette.isDark ? blackAlpha(0.2) : blackAlpha(0.02),
          cursor: isTransitioning || isToggling ? 'default' : 'pointer',
          transition: transition('background', DURATION.fast),
          '&:hover': {
            bgcolor:
              isTransitioning || isToggling
                ? undefined
                : palette.isDark
                  ? blackAlpha(0.3)
                  : blackAlpha(0.04),
          },
        }}
        onClick={handleToggle}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <PowerSettingsNewIcon
            sx={{ fontSize: TYPO.xl, color: isRunning ? STATUS.success : textSecondary }}
          />
          <Box>
            <Typography
              sx={{ fontSize: TYPO.body, fontWeight: FONT_WEIGHT.medium, color: textPrimary }}
            >
              Motor Backend
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mt: 0.25 }}>
              <Box
                sx={{
                  width: 6,
                  height: 6,
                  borderRadius: RADIUS.circle,
                  bgcolor: statusColor,
                }}
              />
              <Typography sx={{ fontSize: TYPO.xs, color: textSecondary }}>
                {statusLabel}
              </Typography>
              {(isTransitioning || isToggling) && (
                <CircularProgress size={10} sx={{ color: textSecondary, ml: 0.5 }} />
              )}
            </Box>
          </Box>
        </Box>
        <Switch
          checked={isRunning}
          disabled={isTransitioning || isToggling}
          size="small"
          color="primary"
        />
      </Box>

      <Typography sx={{ fontSize: TYPO.xs, color: textSecondary, mt: 1, ml: 0.5, lineHeight: 1.5 }}>
        {isRunning
          ? 'Turn off to disable motors and put the robot to sleep.'
          : 'Turn on to wake up the robot and enable motor control.'}
      </Typography>
    </Box>
  );
}
