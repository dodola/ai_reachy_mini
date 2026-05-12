import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import WifiOffIcon from '@mui/icons-material/WifiOff';
import PlaylistAddCheckIcon from '@mui/icons-material/PlaylistAddCheck';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
// TODO(ts): FullscreenOverlay is a .jsx file whose JSDoc produces a bogus
// `IntrinsicAttributes & boolean` prop type when imported by .tsx files.
// Cast to a permissive component type until FullscreenOverlay is migrated.
import FullscreenOverlayRaw from '@components/FullscreenOverlay';
const FullscreenOverlay = FullscreenOverlayRaw as unknown as React.ComponentType<
  Record<string, unknown> & { children?: React.ReactNode }
>;
import LogConsole from '@components/LogConsole';
import { useActiveRobotContext } from '../../context';
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

const LOG_CONSOLE_SX = {
  bgcolor: 'transparent',
  border: 'none',
  borderRadius: 0,
};

interface AppInfo {
  name: string;
  description?: string;
  author?: string;
  downloads?: number;
  icon?: string;
  extra?: {
    cardData?: {
      emoji?: string;
    };
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

interface JobInfo {
  logs?: string[];
  isNetworkError?: boolean;
  [key: string]: unknown;
}

interface InstallOverlayProps {
  appInfo: AppInfo | null;
  jobInfo: JobInfo | null | undefined;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  jobType?: 'install' | 'remove' | 'update' | string;
  resultState?: 'success' | 'failed' | null;
  installStartTime?: number | null;
}

export default function InstallOverlay({
  appInfo,
  jobInfo,
  jobType = 'install',
  resultState = null,
  installStartTime = null,
}: InstallOverlayProps): React.ReactElement | null {
  const palette = useAppPalette();
  const { actions } = useActiveRobotContext();
  const { unlockInstall } = actions;
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [logsExpanded, setLogsExpanded] = useState<boolean>(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const persistedLogsRef = useRef<string[]>([]);
  const maxProgressRef = useRef<number>(0);
  const currentAppNameRef = useRef<string | null>(null);

  const isNetworkError = jobInfo?.isNetworkError === true;

  useEffect(() => {
    if (appInfo?.name && appInfo.name !== currentAppNameRef.current) {
      currentAppNameRef.current = appInfo.name;
      persistedLogsRef.current = [];
      maxProgressRef.current = 0;
    }
  }, [appInfo?.name]);

  useEffect(() => {
    if (jobInfo?.logs && Array.isArray(jobInfo.logs) && jobInfo.logs.length > 0) {
      if (jobInfo.logs.length >= persistedLogsRef.current.length) {
        persistedLogsRef.current = jobInfo.logs;
      } else if (jobInfo.logs.length < persistedLogsRef.current.length) {
        const existing = new Set(persistedLogsRef.current);
        const newLogs = jobInfo.logs.filter(log => !existing.has(log));
        if (newLogs.length > 0) {
          persistedLogsRef.current = [...persistedLogsRef.current, ...newLogs];
        }
      }

      if (persistedLogsRef.current.length > maxProgressRef.current) {
        maxProgressRef.current = persistedLogsRef.current.length;
      }
    }
  }, [jobInfo?.logs]);

  const overlayStartTimeRef = useRef<number | null>(null);

  useEffect(() => {
    if (!appInfo) {
      setElapsedTime(0);
      overlayStartTimeRef.current = null;
      return;
    }

    if (!overlayStartTimeRef.current) {
      overlayStartTimeRef.current = Date.now();
    }

    const startTime = installStartTime || overlayStartTimeRef.current;

    const updateElapsedTime = (): void => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setElapsedTime(elapsed);
    };

    updateElapsedTime();

    if (resultState === null) {
      intervalRef.current = setInterval(updateElapsedTime, 1000);
    } else {
      updateElapsedTime();
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [appInfo, installStartTime, resultState]);

  const currentLogs =
    jobInfo?.logs && jobInfo.logs.length > 0 ? jobInfo.logs : persistedLogsRef.current;

  const phaseInfo = useMemo(() => {
    if (!currentLogs || currentLogs.length === 0) {
      return { phase: 'Preparing', step: 0 };
    }

    const tail = currentLogs.slice(-20);
    const logsText = tail.join(' ').toLowerCase();
    const logCount = currentLogs.length;

    if (logsText.includes('completed') || logsText.includes('success')) {
      return { phase: 'Finalizing', step: 4 };
    }
    if (
      logsText.includes('configuring') ||
      logsText.includes('setting up') ||
      logsText.includes('installing dependencies')
    ) {
      return { phase: 'Configuring', step: 3 };
    }
    if (
      logsText.includes('installing') ||
      logsText.includes('copying') ||
      logsText.includes('extracting')
    ) {
      return { phase: 'Installing', step: 2 };
    }
    if (
      logsText.includes('downloading') ||
      logsText.includes('fetching') ||
      logsText.includes('retrieving')
    ) {
      return { phase: 'Downloading', step: 1 };
    }

    return { phase: 'Processing', step: Math.min(5, Math.floor(logCount / 10) + 1) };
  }, [currentLogs]);

  const latestLogs = useMemo(
    () => (currentLogs.length > 0 ? currentLogs.slice(-5) : []),
    [currentLogs]
  );

  if (!appInfo) return null;

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const isInstalling = jobType === 'install' || jobType === 'update';
  const jobLabel =
    jobType === 'update' ? 'Update' : jobType === 'install' ? 'Installation' : 'Uninstallation';
  const jobLabelProgress =
    jobType === 'update' ? 'Updating' : jobType === 'install' ? 'Installing' : 'Uninstalling';

  const isShowingResult = resultState !== null;

  // TODO(style-migration): warning amber tint is not yet in the palette.
  const warningSurface = 'rgba(245, 158, 11, 0.1)';
  const warningBorder = 'rgba(245, 158, 11, 0.3)';
  const errorSurface = 'rgba(239, 68, 68, 0.1)';
  const errorBorder = 'rgba(239, 68, 68, 0.3)';

  return (
    <FullscreenOverlay
      open={!!appInfo}
      onClose={() => {
        unlockInstall();
      }}
      debugName="InstallProgress"
      onBackdropClick={() => {
        if (isShowingResult && resultState === 'failed') {
          unlockInstall();
        }
      }}
      darkMode={palette.isDark}
      zIndex={10003}
      backdropBlur={0}
      backdropOpacity={1}
      showCloseButton={isShowingResult && resultState === 'failed'}
      centered={true}
    >
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 2,
          maxWidth: '500px',
          width: '90%',
        }}
      >
        {isShowingResult && resultState === 'failed' ? (
          <Box
            sx={{
              width: 120,
              height: 120,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '60px',
              bgcolor: isNetworkError ? warningSurface : errorSurface,
              border: `3px solid ${isNetworkError ? warningBorder : errorBorder}`,
            }}
          >
            {isNetworkError ? (
              <WifiOffIcon
                sx={{
                  fontSize: 64,
                  color: palette.statusWarning,
                }}
              />
            ) : (
              <ErrorOutlineIcon
                sx={{
                  fontSize: 64,
                  color: palette.statusError,
                }}
              />
            )}
          </Box>
        ) : (
          <Box
            sx={{
              fontSize: 64,
              width: 100,
              height: 100,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '24px',
              bgcolor: palette.isDark ? whiteAlpha(0.04) : blackAlpha(0.03),
              border: `2px solid ${palette.border}`,
              animation: 'pulse 2s ease-in-out infinite',
              '@keyframes pulse': {
                '0%, 100%': { transform: 'scale(1)' },
                '50%': { transform: 'scale(1.05)' },
              },
            }}
          >
            {[...(appInfo.extra?.cardData?.emoji || appInfo.icon || '📦')][0]}
          </Box>
        )}

        {isShowingResult && resultState === 'failed' ? (
          <Box sx={{ textAlign: 'center', maxWidth: '380px' }}>
            <Typography
              sx={{
                fontSize: 24,
                fontWeight: FONT_WEIGHT.semibold,
                color: isNetworkError ? palette.statusWarning : palette.statusError,
                mb: 0.5,
                animation: 'fadeInScale 0.5s ease',
                '@keyframes fadeInScale': {
                  from: { opacity: 0, transform: 'scale(0.9)' },
                  to: { opacity: 1, transform: 'scale(1)' },
                },
              }}
            >
              {isNetworkError ? 'Network Issue' : `${jobLabel} Failed`}
            </Typography>
            <Typography
              sx={{
                fontSize: TYPO.lg,
                fontWeight: FONT_WEIGHT.medium,
                color: palette.textSecondary,
                mb: isNetworkError ? 1.5 : 0,
              }}
            >
              {appInfo.name}
            </Typography>
            {isNetworkError && (
              <Typography
                sx={{
                  fontSize: TYPO.body,
                  color: palette.textMuted,
                  lineHeight: 1.5,
                }}
              >
                The download seems stuck. Please check your internet connection and try again later.
              </Typography>
            )}
          </Box>
        ) : (
          <Box
            sx={{
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              gap: 0.25,
              mb: -0.5,
            }}
          >
            <Typography
              sx={{
                fontSize: TYPO.tiny,
                fontWeight: FONT_WEIGHT.medium,
                color: palette.textMuted,
                letterSpacing: '1px',
                textTransform: 'uppercase',
              }}
            >
              {jobLabelProgress}
            </Typography>
            <Typography
              sx={{
                fontSize: 24,
                fontWeight: FONT_WEIGHT.semibold,
                color: palette.textPrimary,
                letterSpacing: '-0.3px',
              }}
            >
              {appInfo.name}
            </Typography>
          </Box>
        )}

        <>
          {!isShowingResult && (
            <Box sx={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography
                sx={{
                  fontSize: TYPO.body,
                  color: palette.textSecondary,
                  lineHeight: 1.5,
                  maxWidth: '420px',
                }}
              >
                {appInfo.description || 'No description'}
              </Typography>

              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  justifyContent: 'center',
                  flexWrap: 'wrap',
                }}
              >
                {appInfo.author && (
                  <Typography
                    sx={{
                      fontSize: TYPO.xs,
                      fontWeight: FONT_WEIGHT.semibold,
                      color: palette.textMuted,
                    }}
                  >
                    by {appInfo.author}
                  </Typography>
                )}

                {appInfo.downloads !== undefined && (
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 0.5,
                      px: 1,
                      py: 0.25,
                      borderRadius: RADIUS.md,
                      bgcolor: palette.isDark ? whiteAlpha(0.05) : blackAlpha(0.03),
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize: TYPO.xs,
                        fontWeight: FONT_WEIGHT.semibold,
                        color: palette.textSecondary,
                      }}
                    >
                      {appInfo.downloads} downloads
                    </Typography>
                  </Box>
                )}
              </Box>
            </Box>
          )}

          {!isShowingResult && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                mt: 1.5,
              }}
            >
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  px: 2,
                  py: 1,
                  borderRadius: RADIUS.lg,
                  bgcolor: accentAlpha(palette.isDark ? 0.08 : 0.05),
                  border: `1px solid ${accentAlpha(palette.isDark ? 0.2 : 0.15)}`,
                }}
              >
                <CircularProgress size={14} thickness={5} sx={{ color: ACCENT.main }} />
                <Typography
                  sx={{
                    fontSize: TYPO.sm,
                    fontWeight: FONT_WEIGHT.semibold,
                    color: ACCENT.main,
                    fontFamily: 'monospace',
                  }}
                >
                  {formatTime(elapsedTime)}
                </Typography>
              </Box>

              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.75,
                  px: 1.5,
                  py: 1,
                  borderRadius: RADIUS.lg,
                  bgcolor: accentAlpha(palette.isDark ? 0.08 : 0.05),
                  border: `1px solid ${accentAlpha(palette.isDark ? 0.2 : 0.15)}`,
                }}
              >
                <PlaylistAddCheckIcon sx={{ fontSize: TYPO.md, color: ACCENT.main }} />
                <Typography
                  sx={{
                    fontSize: TYPO.sm,
                    fontWeight: FONT_WEIGHT.semibold,
                    color: ACCENT.main,
                    fontFamily: 'monospace',
                  }}
                >
                  {phaseInfo.phase}
                </Typography>
              </Box>
            </Box>
          )}

          <Accordion
            expanded={logsExpanded}
            onChange={(_e, expanded) => setLogsExpanded(expanded)}
            TransitionProps={{ timeout: 0 }}
            sx={{
              width: '100%',
              maxWidth: '460px',
              bgcolor: 'transparent !important',
              boxShadow: 'none !important',
              '&:before': { display: 'none' },
              '&.Mui-expanded': { margin: 0 },
            }}
          >
            <AccordionSummary
              expandIcon={
                <ExpandMoreIcon
                  sx={{
                    color: palette.textMuted,
                    fontSize: TYPO.xl,
                  }}
                />
              }
              sx={{
                minHeight: 'auto !important',
                py: 1,
                px: 1.5,
                borderRadius: RADIUS.xl,
                bgcolor: palette.isDark ? blackAlpha(0.2) : blackAlpha(0.02),
                border: `1px solid ${palette.isDark ? whiteAlpha(0.05) : blackAlpha(0.05)}`,
                '&:hover': {
                  bgcolor: palette.isDark ? blackAlpha(0.3) : blackAlpha(0.04),
                },
                '&.Mui-expanded': {
                  minHeight: 'auto !important',
                  borderBottomLeftRadius: 0,
                  borderBottomRightRadius: 0,
                },
                '& .MuiAccordionSummary-content': {
                  margin: '8px 0 !important',
                  '&.Mui-expanded': {
                    margin: '8px 0 !important',
                  },
                },
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                <Typography
                  sx={{
                    fontSize: TYPO.xs,
                    fontWeight: FONT_WEIGHT.medium,
                    color: palette.textSecondary,
                  }}
                >
                  {logsExpanded ? 'Hide logs' : 'Show logs'}
                </Typography>
                {!logsExpanded && latestLogs.length > 0 && (
                  <Typography
                    sx={{
                      fontSize: TYPO.tiny,
                      color: palette.textMuted,
                      ml: 'auto',
                    }}
                  >
                    {latestLogs.length} {latestLogs.length === 1 ? 'recent log' : 'recent logs'}
                  </Typography>
                )}
              </Box>
            </AccordionSummary>
            <AccordionDetails
              sx={{
                p: 0,
                border: `1px solid ${palette.isDark ? whiteAlpha(0.05) : blackAlpha(0.05)}`,
                borderTop: 'none',
                borderBottomLeftRadius: RADIUS.xl,
                borderBottomRightRadius: RADIUS.xl,
                bgcolor: palette.isDark ? blackAlpha(0.2) : blackAlpha(0.02),
              }}
            >
              <LogConsole
                logs={currentLogs}
                darkMode={palette.isDark}
                includeStoreLogs={false}
                maxHeight="140px"
                showTimestamp={false}
                simpleStyle={true}
                compact={false}
                sx={LOG_CONSOLE_SX}
              />
            </AccordionDetails>
          </Accordion>

          {!isShowingResult && isInstalling && (
            <Typography
              sx={{
                fontSize: TYPO.xs,
                color: palette.textMuted,
                fontStyle: 'italic',
                mt: 1,
              }}
            >
              This may take up to 1 minute...
            </Typography>
          )}
        </>
      </Box>
    </FullscreenOverlay>
  );
}
