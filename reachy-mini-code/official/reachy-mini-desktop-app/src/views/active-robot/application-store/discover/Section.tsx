import React from 'react';
import { Box, Typography, Button, InputBase, CircularProgress, Tooltip } from '@mui/material';
import DownloadOutlinedIcon from '@mui/icons-material/DownloadOutlined';
import SearchIcon from '@mui/icons-material/Search';
import StarOutlineIcon from '@mui/icons-material/StarOutline';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import ReachyBox from '../../../../assets/reachy-update-box.svg';
import { useActiveRobotContext } from '../../context';
import hfLogo from '../../../../assets/hf-logo.svg';
import {
  ACCENT,
  DURATION,
  FONT_WEIGHT,
  RADIUS,
  STATUS,
  TYPO,
  accentAlpha,
  blackAlpha,
  transition,
  whiteAlpha,
} from '@styles/tokens';
import { useAppPalette } from '@styles';

interface AppLike {
  name: string;
  description?: string;
  url?: string;
  extra?: {
    lastModified?: string | number | Date;
    likes?: number;
    cardData?: {
      emoji?: string;
    };
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

interface JobInfo {
  status?: string;
  logs?: string[];
  [key: string]: unknown;
}

interface DiscoverAppsSectionProps {
  filteredApps: AppLike[];
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  isBusy: boolean;
  activeJobs: unknown;
  isJobRunning: (appName: string, type: string) => boolean;
  handleInstall: (app: AppLike) => void;
  getJobInfo: (appName: string, type: string) => JobInfo | null | undefined;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  onOpenCreateTutorial: () => void;
}

// Amber-accent badge colors. `AMBER_LIGHT` aligns with `STATUS.warning`;
// `AMBER_DARK` is a slightly lighter amber used only on dark surfaces.
// TODO(style-migration): promote AMBER_DARK and the bg/border rgba variants
// to palette tokens once they appear outside the app store.
const AMBER_DARK = '#fbbf24';
const AMBER_LIGHT = STATUS.warning;
const AMBER_BG_DARK = 'rgba(251, 191, 36, 0.08)';
const AMBER_BG_LIGHT = 'rgba(245, 158, 11, 0.08)';
const AMBER_BORDER_DARK = 'rgba(251, 191, 36, 0.2)';
const AMBER_BORDER_LIGHT = 'rgba(245, 158, 11, 0.2)';

export default function DiscoverAppsSection({
  filteredApps,
  isBusy,
  isJobRunning,
  handleInstall,
  getJobInfo,
  searchQuery,
  setSearchQuery,
  onOpenCreateTutorial,
}: DiscoverAppsSectionProps): React.ReactElement {
  const palette = useAppPalette();
  const { shellApi } = useActiveRobotContext();
  const open = shellApi.open;
  return (
    <Box sx={{ px: 3, pb: 3 }}>
      <Box
        sx={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', mb: 1.5 }}
      >
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography
              sx={{
                fontSize: TYPO.xs,
                fontWeight: FONT_WEIGHT.bold,
                color: palette.textSecondary,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}
            >
              Discover
            </Typography>
            <Tooltip
              title="Browse and install new apps from Hugging Face Spaces. Search for apps that extend Reachy's capabilities."
              arrow
              placement="top"
            >
              <InfoOutlinedIcon
                sx={{
                  fontSize: TYPO.sm,
                  color: palette.textMuted,
                  opacity: 0.6,
                  cursor: 'help',
                }}
              />
            </Tooltip>
          </Box>
          <Typography
            sx={{
              fontSize: TYPO.xs,
              fontWeight: FONT_WEIGHT.bold,
              color: palette.textMuted,
            }}
          >
            {filteredApps.length}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography
            sx={{
              fontSize: TYPO.tiny,
              color: palette.textMuted,
              fontWeight: FONT_WEIGHT.medium,
            }}
          >
            from
          </Typography>
          <Box
            component="img"
            src={hfLogo}
            alt="Hugging Face"
            sx={{
              height: 14,
              width: 'auto',
              opacity: 1,
            }}
          />
          <Typography
            sx={{
              fontSize: TYPO.tiny,
              color: palette.textMuted,
              fontWeight: FONT_WEIGHT.medium,
            }}
          >
            Hugging Face
          </Typography>
        </Box>
      </Box>

      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          px: 1.5,
          py: 0.75,
          mb: 2,
          borderRadius: RADIUS.lg,
          bgcolor: palette.isDark ? '#262626' : 'white',
          border: `1px solid ${palette.border}`,
          transition: transition('box-shadow', DURATION.base),
          '&:focus-within': {
            borderColor: ACCENT.main,
            boxShadow: `0 0 0 3px ${accentAlpha(0.08)}`,
          },
        }}
      >
        <SearchIcon sx={{ fontSize: TYPO.lg, color: palette.textMuted }} />
        <InputBase
          placeholder="Search apps..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          sx={{
            flex: 1,
            fontSize: TYPO.sm,
            fontWeight: FONT_WEIGHT.medium,
            color: palette.textPrimary,
            '& input::placeholder': {
              color: palette.textMuted,
              opacity: 1,
            },
          }}
        />

        <Typography
          sx={{
            fontSize: TYPO.xs,
            fontWeight: FONT_WEIGHT.bold,
            color: palette.textMuted,
            letterSpacing: '0.2px',
          }}
        >
          {filteredApps.length}
        </Typography>

        {searchQuery && (
          <>
            <Box sx={{ width: '1px', height: '14px', bgcolor: palette.border }} />
            <Typography
              onClick={() => setSearchQuery('')}
              sx={{
                fontSize: TYPO.xs,
                color: palette.textMuted,
                cursor: 'pointer',
                fontWeight: FONT_WEIGHT.semibold,
                '&:hover': { color: palette.textSecondary },
              }}
            >
              Clear
            </Typography>
          </>
        )}
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {filteredApps.length === 0 ? (
          <Box
            sx={{
              py: 4,
              textAlign: 'center',
            }}
          >
            <Typography sx={{ fontSize: TYPO.sm, color: palette.textMuted }}>
              No apps found for &quot;{searchQuery}&quot;
            </Typography>
          </Box>
        ) : (
          filteredApps.map(app => {
            const installJob = getJobInfo(app.name, 'install');
            const isInstalling = isJobRunning(app.name, 'install');
            const installFailed = !!(installJob && installJob.status === 'failed');

            return (
              <Box
                key={app.name}
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  p: 2.5,
                  borderRadius: RADIUS.xxl,
                  bgcolor: installFailed
                    ? palette.isDark
                      ? 'rgba(239, 68, 68, 0.04)'
                      : 'rgba(239, 68, 68, 0.02)'
                    : isInstalling
                      ? accentAlpha(palette.isDark ? 0.04 : 0.02)
                      : palette.isDark
                        ? whiteAlpha(0.02)
                        : 'white',
                  border: installFailed
                    ? `1.5px solid ${palette.statusError}`
                    : isInstalling
                      ? `1.5px solid ${accentAlpha(0.3)}`
                      : `1px solid ${palette.border}`,
                  position: 'relative',
                  overflow: 'hidden',
                  boxShadow: 'none',
                  ...(isInstalling && {
                    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                    '@keyframes pulse': {
                      '0%, 100%': {
                        opacity: 1,
                        borderColor: accentAlpha(0.3),
                      },
                      '50%': {
                        opacity: 0.95,
                        borderColor: accentAlpha(0.5),
                      },
                    },
                  }),
                }}
              >
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <Box
                    sx={{
                      fontSize: 28,
                      width: 52,
                      height: 52,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: RADIUS.xl,
                      bgcolor: palette.isDark ? whiteAlpha(0.04) : blackAlpha(0.03),
                      border: `1px solid ${palette.border}`,
                      flexShrink: 0,
                    }}
                  >
                    {[...(app.extra?.cardData?.emoji || '📦')][0]}
                  </Box>

                  <Box sx={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        justifyContent: 'space-between',
                        mb: 0.5,
                      }}
                    >
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography
                          sx={{
                            fontSize: TYPO.md,
                            fontWeight: FONT_WEIGHT.bold,
                            color: palette.textPrimary,
                            lineHeight: 1.3,
                            mb: 0.3,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {app.name}
                        </Typography>

                        {app.extra?.lastModified && (
                          <Typography
                            sx={{
                              fontSize: TYPO.micro,
                              fontWeight: FONT_WEIGHT.medium,
                              color: palette.textMuted,
                              fontFamily: 'monospace',
                              letterSpacing: '0.2px',
                            }}
                          >
                            Updated{' '}
                            {new Date(app.extra.lastModified).toLocaleDateString('en-US', {
                              day: 'numeric',
                              month: 'short',
                              year: 'numeric',
                            })}
                          </Typography>
                        )}
                      </Box>

                      <Button
                        variant="outlined"
                        color="primary"
                        size="small"
                        disabled={isBusy}
                        onClick={() => handleInstall(app)}
                        endIcon={
                          isInstalling ? (
                            <CircularProgress size={12} sx={{ color: ACCENT.main }} />
                          ) : (
                            <DownloadOutlinedIcon sx={{ fontSize: TYPO.body }} />
                          )
                        }
                        sx={{
                          minWidth: 'auto',
                          px: 1.75,
                          py: 0.75,
                          fontSize: TYPO.xs,
                          fontWeight: FONT_WEIGHT.semibold,
                          textTransform: 'none',
                          borderRadius: RADIUS.md,
                          flexShrink: 0,
                          bgcolor: 'transparent',
                          color: ACCENT.main,
                          border: `1px solid ${ACCENT.main}`,
                          transition: transition('all', DURATION.base),
                          '&:hover': {
                            bgcolor: accentAlpha(0.08),
                            borderColor: ACCENT.main,
                          },
                          '&:disabled': {
                            bgcolor: 'transparent',
                            color: palette.textDisabled,
                            borderColor: palette.border,
                          },
                        }}
                      >
                        {isInstalling ? 'Installing...' : 'Install'}
                      </Button>
                    </Box>

                    <Typography
                      sx={{
                        fontSize: TYPO.xs,
                        color: palette.textSecondary,
                        lineHeight: 1.6,
                        mb: 1.5,
                      }}
                    >
                      {app.description || 'No description'}
                    </Typography>

                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                      {app.extra?.likes !== undefined && (
                        <Box
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 0.5,
                            height: 22,
                            px: 1,
                            borderRadius: '11px',
                            bgcolor: palette.isDark ? AMBER_BG_DARK : AMBER_BG_LIGHT,
                            border: `1px solid ${palette.isDark ? AMBER_BORDER_DARK : AMBER_BORDER_LIGHT}`,
                          }}
                        >
                          <Typography
                            sx={{
                              fontSize: TYPO.tiny,
                              fontWeight: FONT_WEIGHT.semibold,
                              color: palette.isDark ? AMBER_DARK : AMBER_LIGHT,
                              lineHeight: 1,
                            }}
                          >
                            {app.extra.likes}
                          </Typography>
                          <StarOutlineIcon
                            sx={{
                              fontSize: TYPO.body,
                              color: palette.isDark ? AMBER_DARK : AMBER_LIGHT,
                            }}
                          />
                        </Box>
                      )}

                      <Box
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: 22,
                          height: 22,
                          borderRadius: '11px',
                          bgcolor: palette.isDark ? whiteAlpha(0.06) : blackAlpha(0.04),
                          border: `1px solid ${palette.border}`,
                        }}
                      >
                        <svg
                          width="12"
                          height="12"
                          viewBox="0 0 25 25"
                          xmlns="http://www.w3.org/2000/svg"
                          aria-hidden="true"
                          focusable="false"
                          role="img"
                          style={{ color: palette.textSecondary }}
                        >
                          <path
                            opacity=".5"
                            d="M6.016 14.674v4.31h4.31v-4.31h-4.31ZM14.674 14.674v4.31h4.31v-4.31h-4.31ZM6.016 6.016v4.31h4.31v-4.31h-4.31Z"
                            fill="currentColor"
                          ></path>
                          <path
                            opacity=".75"
                            fillRule="evenodd"
                            clipRule="evenodd"
                            d="M3 4.914C3 3.857 3.857 3 4.914 3h6.514c.884 0 1.628.6 1.848 1.414a5.171 5.171 0 0 1 7.31 7.31c.815.22 1.414.964 1.414 1.848v6.514A1.914 1.914 0 0 1 20.086 22H4.914A1.914 1.914 0 0 1 3 20.086V4.914Zm3.016 1.102v4.31h4.31v-4.31h-4.31Zm0 12.968v-4.31h4.31v4.31h-4.31Zm8.658 0v-4.31h4.31v4.31h-4.31Zm0-10.813a2.155 2.155 0 1 1 4.31 0 2.155 2.155 0 0 1-4.31 0Z"
                            fill="currentColor"
                          ></path>
                          <path
                            opacity=".25"
                            d="M16.829 6.016a2.155 2.155 0 1 0 0 4.31 2.155 2.155 0 0 0 0-4.31Z"
                            fill="currentColor"
                          ></path>
                        </svg>
                      </Box>

                      <Box sx={{ flex: 1 }} />

                      {app.url && (
                        <Typography
                          onClick={async () => {
                            try {
                              await open(app.url as string);
                            } catch (err) {
                              console.error('Failed to open space URL:', err);
                            }
                          }}
                          sx={{
                            fontSize: TYPO.tiny,
                            fontWeight: FONT_WEIGHT.medium,
                            color: palette.textMuted,
                            textDecoration: 'none',
                            cursor: 'pointer',
                            transition: transition('all', DURATION.fast),
                            display: 'flex',
                            alignItems: 'center',
                            gap: 0.3,
                            '&:hover': {
                              color: ACCENT.main,
                            },
                          }}
                        >
                          View Space →
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </Box>
              </Box>
            );
          })
        )}

        <Box
          component="button"
          onClick={onOpenCreateTutorial}
          sx={{
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            gap: 2,
            p: 2.5,
            borderRadius: RADIUS.xxl,
            bgcolor: 'transparent',
            border: `1px dashed ${accentAlpha(palette.isDark ? 0.4 : 0.5)}`,
            cursor: 'pointer',
            transition: transition('all', DURATION.medium),
            position: 'relative',
            overflow: 'hidden',
            '&:hover': {
              borderColor: accentAlpha(palette.isDark ? 0.6 : 0.7),
              bgcolor: accentAlpha(palette.isDark ? 0.05 : 0.03),
              transform: 'translateY(-1px)',
              boxShadow: `0 4px 12px ${accentAlpha(palette.isDark ? 0.15 : 0.1)}`,
              '& > :last-child': {
                transform: 'translateX(2px)',
              },
            },
            '&:active': {
              transform: 'translateY(0)',
            },
          }}
        >
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: RADIUS.xl,
              bgcolor: accentAlpha(palette.isDark ? 0.08 : 0.05),
              border: theme => `1px solid ${theme.palette.primary.main}40`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: transition('all', DURATION.medium),
            }}
          >
            <Box
              component="img"
              src={ReachyBox}
              alt="Reachy Box"
              sx={{
                width: 24,
                height: 24,
                opacity: palette.isDark ? 0.6 : 0.7,
              }}
            />
          </Box>

          <Box sx={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
            <Typography
              sx={{
                fontSize: TYPO.body,
                fontWeight: FONT_WEIGHT.bold,
                color: accentAlpha(palette.isDark ? 0.6 : 0.7),
                mb: 0.3,
                letterSpacing: '-0.2px',
                textAlign: 'left',
              }}
            >
              Build your own
            </Typography>
            <Typography
              sx={{
                fontSize: TYPO.tiny,
                color: palette.textMuted,
                lineHeight: 1.4,
                textAlign: 'left',
              }}
            >
              Create and share your Reachy Mini app on Hugging Face Spaces
            </Typography>
          </Box>

          <Box
            sx={{
              color: 'primary.main',
              fontSize: TYPO.xl,
              flexShrink: 0,
              transition: transition('transform', DURATION.medium),
            }}
          >
            →
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
