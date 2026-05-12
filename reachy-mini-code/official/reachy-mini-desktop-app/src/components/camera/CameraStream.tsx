/**
 * CameraStream Component
 * Displays the WebRTC video stream from Reachy WiFi camera
 */

import { useRef, useEffect, useState } from 'react';
import { Box, Typography, IconButton, CircularProgress } from '@mui/material';
import VideocamIcon from '@mui/icons-material/Videocam';
import VideocamOffIcon from '@mui/icons-material/VideocamOff';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';
import CloseIcon from '@mui/icons-material/Close';
import RefreshIcon from '@mui/icons-material/Refresh';
import useWebRTCStream, { StreamState } from '../../hooks/media/useWebRTCStream';
import FullscreenOverlayUntyped from '../FullscreenOverlay';
import type React from 'react';
import { ACCENT, STATUS, accentAlpha, whiteAlpha } from '@styles/tokens';
import { useAppPalette, TYPO, FONT_WEIGHT, RADIUS, DURATION, transition } from '@styles';

// TODO(ts): FullscreenOverlay lives outside this agent's migration scope; cast locally
// to a React.FC shape that matches the runtime call signature we use.
const FullscreenOverlay = FullscreenOverlayUntyped as unknown as React.FC<{
  open: boolean;
  onClose: () => void;
  children?: React.ReactNode;
  darkMode?: boolean;
  zIndex?: number;
  centeredX?: boolean;
  centeredY?: boolean;
}>;

export interface CameraStreamProps {
  robotHost: string | null | undefined;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  autoConnect?: boolean;
  onClose?: () => void;
}

/**
 * Camera stream display component
 */
export default function CameraStream({
  robotHost,
  autoConnect = false,
  onClose,
}: CameraStreamProps) {
  const palette = useAppPalette();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showControls, setShowControls] = useState<boolean>(true);
  const controlsTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { state, stream, error, connect, disconnect, isConnected, isConnecting } = useWebRTCStream(
    robotHost,
    autoConnect
  );

  // Attach stream to video element
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream as MediaStream;
      videoRef.current.play().catch((e: unknown) => {
        console.warn('[Camera] Autoplay failed:', e);
      });
    }
  }, [stream]);

  // Auto-hide controls
  useEffect(() => {
    if (isConnected && showControls) {
      controlsTimeoutRef.current = setTimeout(() => {
        setShowControls(false);
      }, 3000);
    }
    return () => {
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
    };
  }, [isConnected, showControls]);

  const handleMouseMove = () => {
    setShowControls(true);
  };

  const handleClose = () => {
    disconnect();
    if (onClose) onClose();
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const videoContent = (
    <Box
      onMouseMove={handleMouseMove}
      onClick={() => setShowControls(true)}
      sx={{
        position: 'relative',
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: '#000',
        borderRadius: isFullscreen ? 0 : RADIUS.xl,
        overflow: 'hidden',
      }}
    >
      {/* Video element */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted={false}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          display: isConnected ? 'block' : 'none',
        }}
      />

      {/* Loading state */}
      {isConnecting && (
        <Box
          sx={{
            position: 'absolute',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
          }}
        >
          <CircularProgress size={40} sx={{ color: ACCENT.main }} />
          <Typography sx={{ color: '#fff', fontSize: TYPO.md }}>Connecting to camera...</Typography>
        </Box>
      )}

      {/* Disconnected state */}
      {state === StreamState.DISCONNECTED && !isConnecting && (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
          }}
        >
          <VideocamOffIcon sx={{ fontSize: 48, color: palette.textMuted }} />
          <Typography sx={{ color: palette.textMuted, fontSize: TYPO.md }}>
            Camera disconnected
          </Typography>
          <IconButton
            onClick={connect}
            sx={{
              color: ACCENT.main,
              border: `1px solid ${ACCENT.main}`,
              '&:hover': { bgcolor: accentAlpha(0.1) },
            }}
          >
            <RefreshIcon />
          </IconButton>
        </Box>
      )}

      {/* Error state */}
      {state === StreamState.ERROR && (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
            p: 3,
          }}
        >
          <VideocamOffIcon sx={{ fontSize: 48, color: STATUS.error }} />
          <Typography sx={{ color: STATUS.error, fontSize: TYPO.md, textAlign: 'center' }}>
            {error || 'Connection failed'}
          </Typography>
          <IconButton
            onClick={connect}
            sx={{
              color: ACCENT.main,
              border: `1px solid ${ACCENT.main}`,
              '&:hover': { bgcolor: accentAlpha(0.1) },
            }}
          >
            <RefreshIcon />
          </IconButton>
        </Box>
      )}

      {/* Controls overlay */}
      {showControls && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            p: 2,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'linear-gradient(to bottom, rgba(0,0,0,0.6), transparent)',
            transition: 'opacity 0.3s',
          }}
        >
          {/* Status badge */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: RADIUS.circle,
                bgcolor: isConnected
                  ? STATUS.success
                  : isConnecting
                    ? STATUS.warning
                    : STATUS.error,
                animation: isConnecting ? 'pulse 1.5s infinite' : 'none',
                '@keyframes pulse': {
                  '0%, 100%': { opacity: 1 },
                  '50%': { opacity: 0.5 },
                },
              }}
            />
            <Typography sx={{ color: '#fff', fontSize: TYPO.sm, fontWeight: FONT_WEIGHT.medium }}>
              {isConnected ? 'Live' : isConnecting ? 'Connecting...' : 'Offline'}
            </Typography>
          </Box>

          {/* Action buttons */}
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton
              onClick={toggleFullscreen}
              size="small"
              sx={{
                color: '#fff',
                bgcolor: whiteAlpha(0.1),
                '&:hover': { bgcolor: whiteAlpha(0.2) },
              }}
            >
              {isFullscreen ? (
                <FullscreenExitIcon sx={{ fontSize: TYPO.xxl }} />
              ) : (
                <FullscreenIcon sx={{ fontSize: TYPO.xxl }} />
              )}
            </IconButton>
            <IconButton
              onClick={handleClose}
              size="small"
              sx={{
                color: '#fff',
                bgcolor: whiteAlpha(0.1),
                '&:hover': { bgcolor: whiteAlpha(0.2) },
              }}
            >
              <CloseIcon sx={{ fontSize: TYPO.xxl }} />
            </IconButton>
          </Box>
        </Box>
      )}
    </Box>
  );

  // Fullscreen mode
  if (isFullscreen) {
    return (
      <FullscreenOverlay
        open={true}
        onClose={() => setIsFullscreen(false)}
        zIndex={10005}
        centeredX={true}
        centeredY={true}
      >
        <Box sx={{ width: '100vw', height: '100vh' }}>{videoContent}</Box>
      </FullscreenOverlay>
    );
  }

  return videoContent;
}

export interface CameraButtonProps {
  onClick: () => void;
  isActive?: boolean;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  disabled?: boolean;
}

/**
 * Camera button to toggle stream visibility
 */
export function CameraButton({ onClick, isActive = false, disabled = false }: CameraButtonProps) {
  const palette = useAppPalette();
  return (
    <IconButton
      onClick={onClick}
      disabled={disabled}
      size="small"
      sx={{
        width: 32,
        height: 32,
        transition: transition('all', DURATION.base),
        color: isActive ? '#fff' : 'primary.main',
        bgcolor: isActive ? 'primary.main' : 'transparent',
        border: '1px solid',
        borderColor: 'primary.main',
        '&:hover': {
          borderColor: 'primary.dark',
          bgcolor: isActive ? 'primary.dark' : accentAlpha(0.08),
        },
        '&:disabled': {
          borderColor: palette.border,
          color: palette.textDisabled,
        },
      }}
    >
      {isActive ? (
        <VideocamIcon sx={{ fontSize: TYPO.xxl }} />
      ) : (
        <VideocamOffIcon sx={{ fontSize: TYPO.xxl }} />
      )}
    </IconButton>
  );
}
