import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { ACCENT, FONT_WEIGHT, TYPO, accentAlpha } from '@styles/tokens';
import { useAppPalette } from '@styles';

interface Category {
  name: string;
  count: number;
}

interface CategoryFiltersProps {
  /** @deprecated Theme mode is now read from `useAppPalette()`. Prop kept for back-compat but ignored. */
  darkMode?: boolean;
  categories: Category[];
  selectedCategory: string | null;
  setSelectedCategory: (category: string | null) => void;
  totalAppsCount: number;
}

export default function CategoryFilters({
  categories,
  selectedCategory,
  setSelectedCategory,
  totalAppsCount,
}: CategoryFiltersProps): React.ReactElement {
  const palette = useAppPalette();
  return (
    <Box
      sx={{
        mt: 0,
        mb: 6,
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 1.5,
        flexWrap: 'wrap',
      }}
    >
      <Typography
        sx={{
          fontSize: TYPO.sm,
          fontWeight: FONT_WEIGHT.semibold,
          color: palette.textSecondary,
        }}
      >
        Tags
      </Typography>
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 1,
          alignItems: 'center',
        }}
      >
        <Chip
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <span>All</span>
              <Typography
                sx={{
                  fontSize: TYPO.xs,
                  fontWeight: FONT_WEIGHT.semibold,
                  color: selectedCategory === null ? ACCENT.main : palette.textMuted,
                  opacity: 0.8,
                }}
              >
                ({totalAppsCount})
              </Typography>
            </Box>
          }
          onClick={() => setSelectedCategory(null)}
          size="small"
          sx={{
            height: 28,
            fontSize: TYPO.sm,
            fontWeight: selectedCategory === null ? FONT_WEIGHT.bold : FONT_WEIGHT.medium,
            bgcolor:
              selectedCategory === null
                ? accentAlpha(palette.isDark ? 0.2 : 0.15)
                : palette.isDark
                  ? 'rgba(255, 255, 255, 0.08)'
                  : 'rgba(0, 0, 0, 0.05)',
            color: selectedCategory === null ? ACCENT.main : palette.textSecondary,
            border:
              selectedCategory === null
                ? `1px solid ${ACCENT.main}`
                : `1px solid ${palette.border}`,
            cursor: 'pointer',
            '&:hover': {
              bgcolor:
                selectedCategory === null
                  ? accentAlpha(palette.isDark ? 0.25 : 0.2)
                  : palette.isDark
                    ? 'rgba(255, 255, 255, 0.12)'
                    : 'rgba(0, 0, 0, 0.08)',
            },
            '& .MuiChip-label': { px: 1.5 },
          }}
        />
        {categories.length > 0 &&
          categories.map(category => {
            const displayName = category.name.startsWith('sdk:')
              ? category.name.replace('sdk:', '').charAt(0).toUpperCase() +
                category.name.replace('sdk:', '').slice(1).toLowerCase()
              : category.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            const isSelected = selectedCategory === category.name;

            return (
              <Chip
                key={category.name}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <span>{displayName}</span>
                    <Typography
                      sx={{
                        fontSize: TYPO.xs,
                        fontWeight: FONT_WEIGHT.semibold,
                        color: isSelected ? ACCENT.main : palette.textMuted,
                        opacity: 0.8,
                      }}
                    >
                      ({category.count})
                    </Typography>
                  </Box>
                }
                onClick={() => setSelectedCategory(isSelected ? null : category.name)}
                size="small"
                sx={{
                  height: 28,
                  fontSize: TYPO.sm,
                  fontWeight: isSelected ? FONT_WEIGHT.bold : FONT_WEIGHT.medium,
                  bgcolor: isSelected
                    ? accentAlpha(palette.isDark ? 0.2 : 0.15)
                    : palette.isDark
                      ? 'rgba(255, 255, 255, 0.08)'
                      : 'rgba(0, 0, 0, 0.05)',
                  color: isSelected ? ACCENT.main : palette.textSecondary,
                  border: isSelected ? `1px solid ${ACCENT.main}` : `1px solid ${palette.border}`,
                  cursor: 'pointer',
                  '&:hover': {
                    bgcolor: isSelected
                      ? accentAlpha(palette.isDark ? 0.25 : 0.2)
                      : palette.isDark
                        ? 'rgba(255, 255, 255, 0.12)'
                        : 'rgba(0, 0, 0, 0.08)',
                  },
                  '& .MuiChip-label': { px: 1.5 },
                }}
              />
            );
          })}
      </Box>
    </Box>
  );
}
