import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  InputBase,
  Tooltip,
  IconButton,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import CloseIcon from '@mui/icons-material/Close';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import {
  ACCENT,
  BLUR,
  DURATION,
  FONT_WEIGHT,
  RADIUS,
  TYPO,
  accentAlpha,
  transition,
} from '@styles/tokens';
import { useAppPalette } from '@styles';

interface SearchBarProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  officialOnly: boolean;
  setOfficialOnly: (value: boolean) => void;
  privateOnly: boolean;
  setPrivateOnly: (value: boolean) => void;
  isLoading: boolean;
  filteredApps: unknown[];
  totalAppsCount: number;
  isFiltered: boolean;
}

export default function SearchBar({
  searchQuery,
  setSearchQuery,
  officialOnly,
  setOfficialOnly,
  privateOnly,
  setPrivateOnly,
  isLoading,
  filteredApps,
  totalAppsCount,
  isFiltered,
}: SearchBarProps): React.ReactElement {
  const palette = useAppPalette();
  const [isSticky, setIsSticky] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    const container = containerRef.current;
    if (!sentinel || !container) return;

    const checkSticky = (): void => {
      const sentinelRect = sentinel.getBoundingClientRect();
      const shouldBeSticky = sentinelRect.top < 0;
      setIsSticky(shouldBeSticky);
    };

    checkSticky();

    let scrollContainer: HTMLElement | null = container;
    while (scrollContainer && scrollContainer !== document.body) {
      const style = window.getComputedStyle(scrollContainer);
      if (style.position === 'fixed' && (style.overflow === 'auto' || style.overflowY === 'auto')) {
        scrollContainer.addEventListener('scroll', checkSticky, { passive: true });
        break;
      }
      scrollContainer = scrollContainer.parentElement;
    }

    const observer = new IntersectionObserver(
      entries => {
        const entry = entries[0];
        setIsSticky(!entry.isIntersecting);
      },
      {
        root: null,
        rootMargin: '0px',
        threshold: 0,
      }
    );

    observer.observe(sentinel);

    return () => {
      observer.disconnect();
      if (scrollContainer && scrollContainer !== document.body) {
        scrollContainer.removeEventListener('scroll', checkSticky);
      }
    };
  }, []);

  // TODO(style-migration): `#8b5cf6` purple is not in the palette; keep literal
  // until a `statusPrivate`/`accentPurple` token is added.
  const PRIVATE_COLOR = '#8b5cf6';

  return (
    <>
      <Box
        ref={sentinelRef}
        sx={{
          position: 'relative',
          height: '1px',
          width: '100%',
          pointerEvents: 'none',
          visibility: 'hidden',
        }}
      />
      <Box
        ref={containerRef}
        sx={{
          position: 'sticky',
          top: 0,
          pt: 1,
          pb: 0,
          mb: 2,
          zIndex: 10,
          bgcolor: isSticky
            ? palette.isDark
              ? 'rgba(18, 18, 18, 0.92)'
              : 'rgba(255, 255, 255, 0.95)'
            : 'transparent',
          backdropFilter: isSticky ? BLUR.md : 'none',
          WebkitBackdropFilter: isSticky ? BLUR.md : 'none',
          transition: transition(['background-color', 'backdrop-filter'], DURATION.base),
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            px: 1.5,
            py: 1.5,
            mt: 3,
            borderRadius: RADIUS.xl,
            bgcolor: palette.isDark ? '#262626' : 'white',
            border: `1px solid ${ACCENT.main}`,
            transition: transition('box-shadow', DURATION.base),
            '&:focus-within': {
              borderColor: ACCENT.main,
              boxShadow: `0 0 0 3px ${accentAlpha(0.08)}`,
            },
          }}
        >
          <Tooltip title="Search for apps by name or description" arrow placement="top">
            <SearchIcon sx={{ fontSize: TYPO.xl, color: palette.textMuted, cursor: 'help' }} />
          </Tooltip>
          <InputBase
            placeholder="Search apps..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            sx={{
              flex: 1,
              fontSize: TYPO.md,
              fontWeight: FONT_WEIGHT.medium,
              color: palette.textPrimary,
              '& input::placeholder': {
                color: palette.textMuted,
                opacity: 1,
              },
            }}
          />

          {searchQuery && (
            <>
              <Box
                sx={{
                  width: '1px',
                  height: '18px',
                  bgcolor: palette.border,
                }}
              />
              <IconButton
                onClick={() => setSearchQuery('')}
                size="small"
                sx={{
                  p: 0.5,
                  color: palette.textMuted,
                  '&:hover': {
                    color: palette.textSecondary,
                    bgcolor: palette.isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.05)',
                  },
                }}
                title="Clear search"
              >
                <CloseIcon sx={{ fontSize: TYPO.xl }} />
              </IconButton>
            </>
          )}

          <Tooltip
            title={`${filteredApps.length} ${filteredApps.length === 1 ? 'app' : 'apps'} ${searchQuery ? 'found' : 'available'}`}
            arrow
            placement="top"
          >
            <Typography
              sx={{
                fontSize: TYPO.xs,
                fontWeight: FONT_WEIGHT.bold,
                color: isFiltered ? ACCENT.main : palette.textMuted,
                letterSpacing: '0.2px',
                cursor: 'help',
                px: 1.5,
                py: 0.5,
                borderRadius: RADIUS.sm,
                bgcolor: isFiltered
                  ? accentAlpha(palette.isDark ? 0.15 : 0.08)
                  : palette.isDark
                    ? 'rgba(255, 255, 255, 0.03)'
                    : 'rgba(0, 0, 0, 0.02)',
                border: isFiltered
                  ? `1px solid ${accentAlpha(palette.isDark ? 0.3 : 0.2)}`
                  : 'none',
              }}
            >
              {isFiltered ? `${filteredApps.length}/${totalAppsCount}` : filteredApps.length}
            </Typography>
          </Tooltip>

          {!officialOnly && (
            <>
              <Box
                sx={{
                  width: '1px',
                  height: '18px',
                  bgcolor: palette.border,
                }}
              />
              <Tooltip
                title="Apps are fetched from Hugging Face Spaces API filtered by 'reachy_mini' tag"
                arrow
                placement="bottom"
                enterDelay={300}
                leaveDelay={0}
                PopperProps={{
                  style: {
                    zIndex: 10010,
                  },
                  container: document.body,
                }}
                slotProps={{
                  tooltip: {
                    sx: {
                      zIndex: '10010 !important',
                      position: 'relative',
                    },
                  },
                }}
              >
                <InfoOutlinedIcon
                  sx={{
                    fontSize: TYPO.lg,
                    color: palette.textMuted,
                    cursor: 'help',
                    flexShrink: 0,
                  }}
                />
              </Tooltip>
            </>
          )}

          <Box
            sx={{
              width: '1px',
              height: '18px',
              bgcolor: palette.border,
            }}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={privateOnly}
                onChange={e => setPrivateOnly(e.target.checked)}
                disabled={isLoading}
                size="small"
                sx={{
                  color: palette.textMuted,
                  '&.Mui-checked': {
                    color: PRIVATE_COLOR,
                  },
                  '&.Mui-disabled': {
                    color: palette.textDisabled,
                    opacity: 0.5,
                  },
                  '& .MuiSvgIcon-root': {
                    fontSize: TYPO.xl,
                  },
                }}
              />
            }
            label={
              <Typography
                sx={{
                  fontSize: TYPO.sm,
                  fontWeight: FONT_WEIGHT.semibold,
                  color: palette.textMuted,
                  userSelect: 'none',
                  whiteSpace: 'nowrap',
                }}
              >
                Private
              </Typography>
            }
            sx={{
              m: 0,
              '& .MuiFormControlLabel-label': {
                ml: 0.5,
              },
            }}
          />

          <Box
            sx={{
              width: '1px',
              height: '18px',
              bgcolor: palette.border,
            }}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={officialOnly}
                onChange={e => setOfficialOnly(e.target.checked)}
                disabled={isLoading}
                size="small"
                sx={{
                  color: palette.textMuted,
                  '&.Mui-checked': {
                    color: ACCENT.main,
                  },
                  '&.Mui-disabled': {
                    color: palette.textDisabled,
                    opacity: 0.5,
                  },
                  '& .MuiSvgIcon-root': {
                    fontSize: TYPO.xl,
                  },
                }}
              />
            }
            label={
              <Typography
                sx={{
                  fontSize: TYPO.sm,
                  fontWeight: FONT_WEIGHT.semibold,
                  color: palette.textMuted,
                  userSelect: 'none',
                  pr: 1.5,
                }}
              >
                Official
              </Typography>
            }
            sx={{
              m: 0,
              '& .MuiFormControlLabel-label': {
                ml: 0.5,
              },
            }}
          />
        </Box>
      </Box>
    </>
  );
}
