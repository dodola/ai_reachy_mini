import { useEffect, useState, useRef } from 'react';
import { Box, Typography, LinearProgress, CircularProgress, Button, Link } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import reachyUpdateBoxSvg from '../../assets/reachy-update-box.svg';
import useAppStore from '../../store/useAppStore';
import { DAEMON_CONFIG } from '../../config/daemon';
import { useInternetHealthcheck } from './hooks';
import PulseButton from '@components/PulseButton';
import LogConsole from '@components/LogConsole';
import {
  ACCENT,
  BLUR,
  DURATION,
  FONT_WEIGHT,
  RADIUS,
  STATUS,
  TYPO,
  blackAlpha,
  hexToRgba,
  transition,
  useAppPalette,
  whiteAlpha,
} from '@styles';

export interface UpdateInfo {
  version: string;
  date: string;
  [key: string]: unknown;
}

export interface UpdateViewProps {
  isChecking: boolean;
  isDownloading: boolean;
  downloadProgress: number;
  updateAvailable: UpdateInfo | null;
  updateError: string | null;
  onInstallUpdate: () => void;
}

/**
 * Update view component
 * Displays "Checking for updates..." for at least 2-3 seconds
 * Automatically installs if an update is available
 */
export default function UpdateView({
  isChecking,
  isDownloading,
  downloadProgress,
  updateAvailable,
  updateError,
  onInstallUpdate,
}: UpdateViewProps) {
  const palette = useAppPalette();
  const isDark = palette.isDark;
  const { skipUpdate } = useAppStore();
  const [minDisplayTimeElapsed, setMinDisplayTimeElapsed] = useState<boolean>(false);
  const checkStartTimeRef = useRef<number>(Date.now());
  const { isOnline: isInternetOnline, hasChecked: hasInternetChecked } = useInternetHealthcheck({
    interval: 5000,
    timeout: 5000,
  });

  // ✅ Timer to guarantee minimum display time (uses centralized config)
  // Reset timer when component mounts to ensure "Looking for updates..." is visible for at least 2 seconds
  // This works in both DEV mode (where isChecking stays false) and PRODUCTION (where check may complete quickly)
  useEffect(() => {
    checkStartTimeRef.current = Date.now();
    setMinDisplayTimeElapsed(false);

    const timer = setTimeout(() => {
      setMinDisplayTimeElapsed(true);
    }, DAEMON_CONFIG.MIN_DISPLAY_TIMES.UPDATE_CHECK);

    return () => clearTimeout(timer);
  }, []); // ✅ Only reset on mount - ensures consistent 2s display regardless of check speed

  // ✅ No automatic installation - user chooses via buttons

  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return dateString;
    }
  };

  // Check if error is network-related
  const isNetworkError = (error: string | null | undefined): boolean => {
    if (!error) return false;

    const errorLower = error.toLowerCase();
    const networkKeywords = [
      'network',
      'connection',
      'internet',
      'timeout',
      'fetch',
      'could not fetch',
      'failed to fetch',
      'unable to check',
      'check your internet',
      'no internet',
      'offline',
    ];

    return networkKeywords.some(keyword => errorLower.includes(keyword));
  };

  return (
    <Box
      sx={{
        width: '100vw',
        height: '100vh',
        // TODO(style-migration): bespoke 0.95 / 0.85 alpha stack doesn't map
        // to a single surface token; `surfaceCard` is the closest match.
        background: palette.surfaceCard,
        backdropFilter: BLUR.lg,
        WebkitBackdropFilter: BLUR.lg,
        overflow: 'hidden',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh', // TopBar is fixed, doesn't take space
          px: 4,
        }}
      >
        {/* ✅ Show "Looking for updates..." if checking OR if minimum time not elapsed yet
            This ensures the message is visible for at least 2 seconds, even if check completes quickly */}
        {(isChecking || !minDisplayTimeElapsed) && !updateAvailable && !updateError ? (
          // State: Checking in progress OR minimum display time not elapsed - subtle and centered design
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <CircularProgress
              size={28}
              thickness={2.5}
              sx={{
                color: palette.border,
                mb: 1.5,
              }}
            />

            <Typography
              sx={{
                fontSize: TYPO.sm,
                fontWeight: FONT_WEIGHT.regular,
                color: palette.textFaint,
                textAlign: 'center',
                letterSpacing: '0.2px',
              }}
            >
              Looking for updates...
            </Typography>
          </Box>
        ) : updateAvailable ? (
          // State: Update available (automatic installation)
          <>
            <Box sx={{ mb: 4 }}>
              <img
                src={reachyUpdateBoxSvg}
                alt="Reachy Update"
                style={
                  {
                    width: '220px',
                    height: '220px',
                    mb: 0,
                  } as React.CSSProperties
                }
              />
            </Box>

            <Typography
              sx={{
                fontSize: 24,
                fontWeight: FONT_WEIGHT.semibold,
                color: palette.textPrimary,
                mb: 1,
                mt: 0,
                textAlign: 'center',
              }}
            >
              Update Available
            </Typography>

            <Typography
              sx={{
                fontSize: TYPO.md,
                color: palette.textSecondary,
                textAlign: 'center',
                maxWidth: 360,
                lineHeight: 1.6,
                mb: 2,
              }}
            >
              Version {updateAvailable.version} • {formatDate(updateAvailable.date)}
            </Typography>

            {/* Link to release notes on website */}
            {!isDownloading && (
              <Link
                href="https://huggingface.co/spaces/pollen-robotics/Reachy_Mini#/download?scrollTo=release-notes"
                target="_blank"
                rel="noopener noreferrer"
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                  color: palette.textMuted,
                  fontSize: TYPO.sm,
                  textDecoration: 'none',
                  mb: 2,
                  '&:hover': {
                    color: ACCENT.main,
                  },
                }}
              >
                View release notes
                <OpenInNewIcon sx={{ fontSize: TYPO.md }} />
              </Link>
            )}

            {/* Progress bar */}
            {(isDownloading || isChecking) && (
              <Box sx={{ width: '100%', maxWidth: 300, mb: 3 }}>
                <LinearProgress
                  variant={isDownloading ? 'determinate' : 'indeterminate'}
                  value={isDownloading ? downloadProgress : undefined}
                  color="primary"
                  sx={{
                    height: 6,
                    borderRadius: 3,
                    bgcolor: isDark ? whiteAlpha(0.1) : blackAlpha(0.1),
                  }}
                />
                {isDownloading && (
                  <Typography
                    sx={{
                      fontSize: TYPO.sm,
                      color: palette.textSecondary,
                      textAlign: 'center',
                      mt: 1,
                    }}
                  >
                    Installing... {downloadProgress}%
                  </Typography>
                )}
              </Box>
            )}

            {/* Error message */}
            {updateError && (
              <Box
                sx={{
                  mb: 3,
                  maxWidth: 360,
                  textAlign: 'center',
                }}
              >
                <Typography
                  sx={{
                    fontSize: TYPO.body,
                    color: STATUS.error,
                    fontWeight: FONT_WEIGHT.medium,
                    mb: 1,
                  }}
                >
                  {updateError}
                </Typography>
              </Box>
            )}

            {/* Action buttons - Update or Skip */}
            {!isDownloading && !updateError && (
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 1.5,
                  mt: 2,
                  width: '100%',
                  maxWidth: 280,
                  alignItems: 'center',
                }}
              >
                <PulseButton
                  onClick={onInstallUpdate}
                  darkMode={isDark}
                  pulse={true}
                  size="medium"
                  sx={{ minWidth: 180 }}
                >
                  Update Now
                </PulseButton>
                <Button
                  variant="text"
                  onClick={skipUpdate}
                  sx={{
                    color: palette.textMuted,
                    fontWeight: FONT_WEIGHT.medium,
                    fontSize: TYPO.body,
                    py: 0.8,
                    textTransform: 'none',
                    '&:hover': {
                      bgcolor: isDark ? whiteAlpha(0.05) : blackAlpha(0.04),
                    },
                  }}
                >
                  Skip for now
                </Button>
              </Box>
            )}
          </>
        ) : updateError ? (
          // State: Error - display clear error message, especially for network errors
          <>
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                maxWidth: 360,
                textAlign: 'center',
              }}
            >
              {/* Icon or visual indicator for error */}
              <Box
                sx={{
                  width: 64,
                  height: 64,
                  borderRadius: '50%',
                  bgcolor: hexToRgba(STATUS.error, isDark ? 0.1 : 0.08),
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mb: 2,
                }}
              >
                <Typography
                  sx={{
                    fontSize: 32,
                    color: STATUS.error,
                  }}
                >
                  ⚠️
                </Typography>
              </Box>

              {/* Error title - more specific based on error type */}
              <Typography
                sx={{
                  fontSize: TYPO.xl,
                  fontWeight: FONT_WEIGHT.semibold,
                  color: palette.textPrimary,
                  mb: 1,
                }}
              >
                {updateError.includes('timed out') || updateError.includes('timeout')
                  ? 'Update Check Timed Out'
                  : updateError.includes('Network error') || updateError.includes('DNS error')
                    ? 'Connection Problem'
                    : updateError.includes('Server error')
                      ? 'Server Error'
                      : updateError.includes('Security error') ||
                          updateError.includes('certificate')
                        ? 'Security Error'
                        : isNetworkError(updateError)
                          ? 'No Internet Connection'
                          : 'Update Check Failed'}
              </Typography>

              {/* Error message - use the detailed error message directly */}
              <Typography
                sx={{
                  fontSize: TYPO.body,
                  color: palette.textSecondary,
                  lineHeight: 1.6,
                  mb: 2,
                  maxWidth: 400,
                }}
              >
                {updateError}
              </Typography>
            </Box>
          </>
        ) : null}
      </Box>

      {/* ✅ LogConsole - fixed at the bottom, always visible with final height */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 16,
          left: '50%',
          transform: 'translateX(-50%)',
          width: 'calc(100% - 32px)',
          maxWidth: '420px',
          zIndex: 1000,
          opacity: 0.2, // Very subtle by default
          transition: 'opacity 0.3s ease-in-out',
          '&:hover': {
            opacity: 1, // Full opacity on hover
          },
        }}
      >
        <LogConsole
          logs={[]}
          darkMode={isDark}
          includeStoreLogs={true}
          compact={true}
          showTimestamp={false}
          lines={2}
          emptyMessage="Waiting for logs..."
          sx={{
            // TODO(style-migration): translucent log-panel backdrops don't map
            // to a shared surface token; derive them from alpha utilities.
            bgcolor: isDark ? blackAlpha(0.6) : whiteAlpha(0.7),
            border: `1px solid ${isDark ? whiteAlpha(0.15) : blackAlpha(0.12)}`,
            backdropFilter: BLUR.sm,
            WebkitBackdropFilter: BLUR.sm,
          }}
        />
      </Box>

      {/* Internet connectivity indicator - discrete pastille above logs */}
      {/* Only display during initial check, hide when update is being downloaded */}
      {hasInternetChecked && !updateAvailable && !isDownloading && (
        <Box
          sx={{
            position: 'absolute',
            bottom: 80, // Above logs console
            left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 1,
            zIndex: 10,
          }}
        >
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: RADIUS.circle,
              bgcolor: isInternetOnline
                ? hexToRgba(STATUS.success, isDark ? 0.6 : 0.5)
                : hexToRgba(STATUS.error, isDark ? 0.6 : 0.5),
              boxShadow: isInternetOnline
                ? `0 0 ${isDark ? 4 : 3}px ${hexToRgba(STATUS.success, isDark ? 0.3 : 0.2)}`
                : `0 0 ${isDark ? 4 : 3}px ${hexToRgba(STATUS.error, isDark ? 0.3 : 0.2)}`,
              transition: transition('all', DURATION.slow),
              flexShrink: 0,
            }}
          />
          <Typography
            sx={{
              fontSize: TYPO.sm,
              fontWeight: FONT_WEIGHT.regular,
              color: isDark ? whiteAlpha(0.7) : blackAlpha(0.7),
              whiteSpace: 'nowrap',
              transition: transition('color', DURATION.slow),
            }}
          >
            {isInternetOnline ? 'Online' : 'Offline'}
          </Typography>
        </Box>
      )}
    </Box>
  );
}
