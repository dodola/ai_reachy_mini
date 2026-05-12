import React, { useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Box, IconButton, Modal } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { getAppWindow } from '../utils/windowUtils';
import { ACCENT, whiteAlpha, blackAlpha } from '@styles/tokens';
import { useAppPalette, TYPO, scrollbarSx } from '@styles';

export interface FullscreenOverlayProps {
  open: boolean;
  onClose: () => void;
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  zIndex?: number;
  showCloseButton?: boolean;
  backdropBlur?: number;
  backdropOpacity?: number;
  centered?: boolean;
  centeredX?: boolean;
  centeredY?: boolean;
  onBackdropClick?: (event: React.MouseEvent<HTMLDivElement>) => void;
  hidden?: boolean;
  keepMounted?: boolean;
  scrollRef?: React.RefObject<HTMLDivElement | null>;
  /** Optional debug label used when tracing overlay lifecycle; unused at runtime. */
  debugName?: string;
  children?: React.ReactNode;
}

export default function FullscreenOverlay({
  open,
  onClose,
  zIndex = 9999,
  showCloseButton = false,
  backdropBlur = 20,
  backdropOpacity,
  centered = true,
  centeredX,
  centeredY,
  onBackdropClick,
  hidden = false,
  keepMounted = false,
  scrollRef,
  children,
}: FullscreenOverlayProps): React.ReactElement {
  const palette = useAppPalette();
  const isDark = palette.isDark;
  const appWindow = getAppWindow();

  const hasAnimatedRef = useRef(false);

  useEffect(() => {
    if (open && !hidden && !hasAnimatedRef.current) {
      hasAnimatedRef.current = true;
    }
  }, [open, hidden]);

  const shouldAnimate = open && !hidden && !hasAnimatedRef.current;
  const defaultBackdropOpacity =
    backdropOpacity !== undefined ? backdropOpacity : isDark ? 0.92 : 0.95;

  const isCenteredX = centeredX !== undefined ? centeredX : centered;
  const isCenteredY = centeredY !== undefined ? centeredY : centered;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (onBackdropClick) {
      onBackdropClick(e);
    } else {
      onClose();
    }
  };

  // TODO(style-migration): overlay backgrounds use parametric opacity rather
  // than a fixed token; keep the isDark branch so the blur scrim still blends
  // cleanly with the app chrome.
  const overlayBgColor = isDark
    ? `rgba(18, 18, 18, ${defaultBackdropOpacity})`
    : `rgba(255, 255, 255, ${defaultBackdropOpacity})`;

  const scrollbarThumb = isDark ? whiteAlpha(0.15) : blackAlpha(0.15);
  const scrollbarThumbHover = isDark ? whiteAlpha(0.25) : blackAlpha(0.25);

  const scrollbarStyles = scrollbarSx(palette, {
    width: 8,
    radius: 4,
    thumb: scrollbarThumb,
    thumbHover: scrollbarThumbHover,
  });

  const closeBtnBg = isDark ? whiteAlpha(0.08) : '#ffffff';
  const closeBtnHoverBg = isDark ? whiteAlpha(0.12) : '#ffffff';

  return (
    <>
      <Modal
        open={open}
        onClose={handleBackdropClick as unknown as () => void}
        keepMounted={keepMounted}
        hideBackdrop
        sx={{
          zIndex,
          ...(hidden && {
            visibility: 'hidden',
            pointerEvents: 'none',
          }),
        }}
      >
        <Box
          ref={scrollRef}
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            outline: 'none',
            bgcolor: overlayBgColor,
            backdropFilter: `blur(${backdropBlur}px)`,
            WebkitBackdropFilter: `blur(${backdropBlur}px)`,
            display: 'flex',
            alignItems: isCenteredY ? 'center' : 'flex-start',
            justifyContent: isCenteredX ? 'center' : 'flex-start',
            overflow: 'auto',
            ...(shouldAnimate && {
              animation: 'overlayFadeIn 0.3s ease forwards',
              '@keyframes overlayFadeIn': {
                from: { opacity: 0 },
                to: { opacity: 1 },
              },
            }),
            ...scrollbarStyles,
          }}
        >
          {/* Drag strip - allows window dragging from the top 33px of the overlay.
              When AppTopBar is present (z-index 10000000), it handles drag and this
              strip is never reached. When AppTopBar is absent (showTopBar: false views),
              this strip provides drag. The close button portal (z-index 10000001) always
              sits above this strip's stacking context (z-index of this modal), so close
              button clicks are never blocked. */}
          <Box
            onMouseDown={async (e: React.MouseEvent<HTMLDivElement>) => {
              e.preventDefault();
              e.stopPropagation();
              try {
                await appWindow.startDragging();
              } catch {
                // ignore drag start failures
              }
            }}
            sx={{
              position: 'absolute',
              top: 0,
              left: 65,
              right: 0,
              height: 33,
              cursor: 'move',
              userSelect: 'none',
              WebkitAppRegion: 'drag',
              zIndex: 1,
            }}
          />

          {/* Content wrapper */}
          <Box
            onClick={(e: React.MouseEvent<HTMLDivElement>) => e.stopPropagation()}
            sx={{
              width: '100%',
              height: isCenteredY ? 'auto' : '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: isCenteredX ? 'center' : 'stretch',
              justifyContent: isCenteredY ? 'center' : 'flex-start',
            }}
          >
            {children}
          </Box>
        </Box>
      </Modal>

      {/* Close button - portal at z-index 10000001, above AppTopBar (10000000).
          This is required because AppTopBar sits at z-index 10000000 to remain
          draggable at all times. Any interactive element within the top 33px of
          a fullscreen overlay must be rendered above it via a portal. */}
      {showCloseButton &&
        open &&
        !hidden &&
        createPortal(
          <IconButton
            onClick={onClose}
            sx={{
              position: 'fixed',
              top: 20,
              right: 16,
              color: ACCENT.main,
              bgcolor: closeBtnBg,
              border: `1px solid ${ACCENT.main}`,
              opacity: 0.7,
              zIndex: 10000001,
              WebkitAppRegion: 'no-drag',
              '&:hover': {
                opacity: 1,
                bgcolor: closeBtnHoverBg,
              },
            }}
          >
            <CloseIcon sx={{ fontSize: TYPO.xxl }} />
          </IconButton>,
          document.body
        )}
    </>
  );
}
