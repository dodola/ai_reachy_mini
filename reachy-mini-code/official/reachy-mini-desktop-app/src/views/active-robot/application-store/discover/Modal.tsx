import React, { useRef, useState, useLayoutEffect } from 'react';
import { Box, CircularProgress, Typography, Button } from '@mui/material';
import WifiOffIcon from '@mui/icons-material/WifiOff';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useVirtualizer } from '@tanstack/react-virtual';
// TODO(ts): FullscreenOverlay is a .jsx file whose JSDoc produces a bogus
// `IntrinsicAttributes & boolean` prop type when imported by .tsx files.
// Cast to a permissive component type until FullscreenOverlay is migrated.
import FullscreenOverlayRaw from '@components/FullscreenOverlay';
const FullscreenOverlay = FullscreenOverlayRaw as unknown as React.ComponentType<
  Record<string, unknown> & { children?: React.ReactNode }
>;
import Header from './components/Header';
import SearchBar from './components/SearchBar';
import CategoryFilters from './components/CategoryFilters';
import AppCard from './components/AppCard';
import EmptyState from './components/EmptyState';
import Footer from './components/Footer';
import {
  FONT_WEIGHT,
  RADIUS,
  STATUS,
  TYPO,
  accentAlpha,
  blackAlpha,
  whiteAlpha,
} from '@styles/tokens';
import { useAppPalette } from '@styles';

const COLUMNS = 2;
const ESTIMATED_ROW_HEIGHT = 240;
const ROW_GAP = 20;

// Amber-accent tones. `AMBER_LIGHT` aligns with `STATUS.warning`;
// `AMBER_DARK` is a brighter amber tuned for dark surfaces.
const AMBER_DARK = '#fbbf24';
const AMBER_LIGHT = STATUS.warning;

interface AppLike {
  name: string;
  description?: string;
  url?: string;
  isInstalled?: boolean;
  [key: string]: unknown;
}

interface JobInfo {
  status?: string;
  logs?: string[];
  [key: string]: unknown;
}

interface Category {
  name: string;
  count: number;
}

interface DiscoverModalProps {
  open: boolean;
  onClose: () => void;
  filteredApps: AppLike[];
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  isBusy: boolean;
  isLoading: boolean;
  error: string | null;
  activeJobs: unknown;
  isJobRunning: (appName: string, type: string) => boolean;
  handleInstall: (app: AppLike) => void;
  getJobInfo: (appName: string, type: string) => JobInfo | null | undefined;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  officialOnly: boolean;
  setOfficialOnly: (value: boolean) => void;
  privateOnly: boolean;
  setPrivateOnly: (value: boolean) => void;
  categories: Category[];
  selectedCategory: string | null;
  setSelectedCategory: (category: string | null) => void;
  totalAppsCount: number;
  installedApps?: AppLike[];
  onOpenCreateTutorial: () => void;
  hidden?: boolean;
}

export default function DiscoverModal({
  open: isOpen,
  onClose,
  filteredApps,
  isBusy,
  isLoading,
  error,
  isJobRunning,
  handleInstall,
  getJobInfo,
  searchQuery,
  setSearchQuery,
  officialOnly,
  setOfficialOnly,
  privateOnly,
  setPrivateOnly,
  categories,
  selectedCategory,
  setSelectedCategory,
  totalAppsCount,
  onOpenCreateTutorial,
  hidden = false,
}: DiscoverModalProps): React.ReactElement {
  const palette = useAppPalette();
  const hasActiveFilter = selectedCategory !== null || (searchQuery && searchQuery.trim());
  const isFiltered = !!hasActiveFilter && filteredApps.length < totalAppsCount;

  const overlayScrollRef = useRef<HTMLDivElement | null>(null);
  const gridAnchorRef = useRef<HTMLDivElement | null>(null);
  const [scrollMargin, setScrollMargin] = useState<number>(0);

  useLayoutEffect(() => {
    if (!gridAnchorRef.current || !overlayScrollRef.current) return;
    const gridTop = gridAnchorRef.current.getBoundingClientRect().top;
    const scrollTop = overlayScrollRef.current.getBoundingClientRect().top;
    setScrollMargin(gridTop - scrollTop + overlayScrollRef.current.scrollTop);
  }, [isOpen, isLoading, filteredApps.length, selectedCategory, searchQuery]);

  const rowCount = Math.ceil(filteredApps.length / COLUMNS);

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => overlayScrollRef.current,
    estimateSize: () => ESTIMATED_ROW_HEIGHT + ROW_GAP,
    overscan: 3,
    scrollMargin,
  });

  return (
    <FullscreenOverlay
      open={isOpen}
      onClose={onClose}
      darkMode={palette.isDark}
      zIndex={10002}
      centeredX={true}
      debugName="DiscoverModalLegacy"
      centeredY={false}
      showCloseButton={true}
      hidden={hidden}
      backdropBlur={10}
      scrollRef={overlayScrollRef}
    >
      <Box
        sx={{
          width: '90%',
          maxWidth: '700px',
          display: 'flex',
          flexDirection: 'column',
          mt: 8,
          mb: 4,
        }}
      >
        <Header />

        <SearchBar
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          officialOnly={officialOnly}
          setOfficialOnly={setOfficialOnly}
          privateOnly={privateOnly}
          setPrivateOnly={setPrivateOnly}
          isLoading={isLoading}
          filteredApps={filteredApps}
          totalAppsCount={totalAppsCount}
          isFiltered={isFiltered}
        />

        <CategoryFilters
          categories={categories}
          selectedCategory={selectedCategory}
          setSelectedCategory={setSelectedCategory}
          totalAppsCount={totalAppsCount}
        />

        {error && filteredApps.length > 0 && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              px: 2.5,
              py: 1.5,
              mb: 2,
              borderRadius: RADIUS.lg,
              backgroundColor: accentAlpha(palette.isDark ? 0.12 : 0.08),
              border: `1px solid ${accentAlpha(palette.isDark ? 0.3 : 0.25)}`,
            }}
          >
            <WifiOffIcon
              sx={{
                fontSize: 20,
                color: palette.isDark ? AMBER_DARK : AMBER_LIGHT,
                flexShrink: 0,
              }}
            />
            <Typography
              sx={{
                fontSize: TYPO.body,
                color: palette.textPrimary,
                fontWeight: FONT_WEIGHT.medium,
                flex: 1,
              }}
            >
              {error}
            </Typography>
          </Box>
        )}

        {error && filteredApps.length === 0 ? (
          <Box
            sx={{
              py: 10,
              textAlign: 'center',
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 2,
            }}
          >
            <WifiOffIcon sx={{ fontSize: 56, color: palette.textMuted, opacity: 0.7, mb: 1 }} />
            <Typography
              sx={{
                fontSize: 15,
                color: palette.textPrimary,
                fontWeight: FONT_WEIGHT.semibold,
                mb: 0.5,
              }}
            >
              No Internet Connection
            </Typography>
            <Typography
              sx={{
                fontSize: TYPO.body,
                color: palette.textSecondary,
                fontWeight: FONT_WEIGHT.regular,
                maxWidth: 320,
                lineHeight: 1.6,
                mb: 2,
              }}
            >
              {error}
            </Typography>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={() => window.location.reload()}
              sx={{
                textTransform: 'none',
                fontSize: TYPO.body,
                fontWeight: FONT_WEIGHT.medium,
                px: 3,
                py: 1,
                borderRadius: RADIUS.md,
                borderColor: palette.borderStrong,
                color: palette.textSecondary,
                '&:hover': {
                  borderColor: palette.borderStrong,
                  backgroundColor: palette.isDark ? whiteAlpha(0.05) : blackAlpha(0.03),
                },
              }}
            >
              Retry
            </Button>
          </Box>
        ) : isLoading ? (
          <Box
            sx={{
              py: 10,
              textAlign: 'center',
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 2,
            }}
          >
            <CircularProgress size={40} sx={{ color: palette.textMuted }} />
            <Typography
              sx={{ fontSize: TYPO.md, color: palette.textMuted, fontWeight: FONT_WEIGHT.medium }}
            >
              Loading apps...
            </Typography>
          </Box>
        ) : filteredApps.length === 0 ? (
          <EmptyState searchQuery={searchQuery} setSearchQuery={setSearchQuery} />
        ) : (
          <Box ref={gridAnchorRef} sx={{ position: 'relative', width: '100%' }}>
            <div
              style={{
                height: virtualizer.getTotalSize(),
                width: '100%',
                position: 'relative',
              }}
            >
              {virtualizer.getVirtualItems().map(virtualRow => {
                const startIdx = virtualRow.index * COLUMNS;
                const app1 = filteredApps[startIdx];
                const app2 = filteredApps[startIdx + 1];

                const getCardProps = (app: AppLike, idx: number) => {
                  const installJob = getJobInfo(app.name, 'install');
                  return {
                    key: app.name,
                    app,
                    isBusy,
                    isInstalling: isJobRunning(app.name, 'install'),
                    installFailed: !!(installJob && installJob.status === 'failed'),
                    isInstalled: app.isInstalled || false,
                    handleInstall,
                    selectedCategory,
                    searchQuery,
                    index: idx,
                  };
                };

                return (
                  <div
                    key={virtualRow.key}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      transform: `translateY(${virtualRow.start - scrollMargin}px)`,
                    }}
                  >
                    <Box sx={{ display: 'flex', gap: 2.5, pb: `${ROW_GAP}px` }}>
                      <AppCard {...getCardProps(app1, startIdx)} />
                      {app2 && <AppCard {...getCardProps(app2, startIdx + 1)} />}
                    </Box>
                  </div>
                );
              })}
            </div>

            <Footer onOpenCreateTutorial={onOpenCreateTutorial} />
          </Box>
        )}
      </Box>
    </FullscreenOverlay>
  );
}
