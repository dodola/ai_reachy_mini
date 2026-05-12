# Bucket 4 - Active robot shell + right panel

> Read [`_shared-context.md`](./_shared-context.md) first.

## Scope (7 files, ~57 ternaries)

- `src/views/active-robot/ActiveRobotView.tsx` (11)
- `src/views/active-robot/right-panel/EmbeddedAppView.tsx` (12)
- `src/views/active-robot/right-panel/RightPanel.tsx` (2)
- `src/views/active-robot/camera/CameraFeed.tsx` (6)
- `src/views/active-robot/audio/AudioControls.tsx` (9)
- `src/views/active-robot/audio/DoAIndicator.tsx` (1)
- `src/views/update/UpdateView.tsx` (16)

**Do NOT touch** (other buckets own them):

- Anything under `src/views/active-robot/application-store/` (bucket 2)
- Anything under `src/views/active-robot/controller/` (bucket 5)
- Anything under `src/views/active-robot/right-panel/applications/` or
  `right-panel/expressions/` - those are either migrated or tracked as TODOs.

## Goal

Introduce `useAppPalette()` where missing, rewrite ternaries, drop store
`darkMode` reads.

## Tokens most useful here

- `palette.textPrimary`, `palette.textSecondary`, `palette.textMuted`,
  `palette.textFaint`
- `palette.surfaceCard`, `palette.surfaceCardHover`, `palette.surfaceSubtle`,
  `palette.surfaceBg`
- `palette.border`, `palette.borderStrong`
- `palette.accentSurface*`, `palette.accentBorder*`, `palette.accentGlow`
- `palette.statusSuccess`, `palette.statusError`, `palette.statusWarning`
  (update/camera banners)
- `palette.statusSuccessSurface | Border | Text` (update banners)
- `palette.shadowMd`, `palette.shadowLg`

## Pitfalls

- `DoAIndicator.tsx` uses a Material Green `#4CAF50` instead of
  `STATUS.success` (`#22c55e`). Keep literal with TODO - the tone matters for
  this specific talking/listening pill.
- `UpdateView.tsx` has 16 ternaries scattered across banners, buttons, and
  dialog content. Be systematic: pass over the whole file once mapping
  text/surface, then again for borders, then accents.

## Definition of done

- `grep -n "darkMode ?" <bucket-files>` returns 0 results (DoAIndicator may
  keep one `palette.isDark` branch for the `#4CAF50` case + TODO comment).
- No `const darkMode = useAppStore((s) => s.darkMode);` in bucket files.
- `./scripts/validate-style-migration.sh` on the bucket scope is green.
- `npm run typecheck` + `npx eslint --fix <files>` clean.
