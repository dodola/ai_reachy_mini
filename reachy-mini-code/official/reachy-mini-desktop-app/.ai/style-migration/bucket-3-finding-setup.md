# Bucket 3 - Finding robot + setup flow

> Read [`_shared-context.md`](./_shared-context.md) first.

## Scope (10 files, ~85 ternaries)

- `src/views/finding-robot/FindingRobotView.tsx` (43)
- `src/views/setup-choice/SetupChoiceView.tsx` (10)
- `src/views/first-time-wifi-setup/FirstTimeWifiSetupView.tsx` (5)
- `src/views/first-time-wifi-setup/steps/Step2ConnectHotspot.tsx` (5)
- `src/views/first-time-wifi-setup/steps/Step1PowerOn.tsx` (0 - sanity check)
- `src/views/permissions-required/PermissionsRequiredView.tsx` (9)
- `src/views/bluetooth-support/BluetoothSupportView.tsx` (5)
- `src/views/starting/StartupView.tsx` (3)
- `src/views/starting/StartingView.tsx` (1)
- `src/views/closing/ClosingView.tsx` (3)

**Do NOT touch** (they have in-flight TODOs tracked separately):

- `src/views/starting/components/StartupLogsPanel.tsx`
- `src/views/starting/components/ScanErrorDisplay.tsx`
- `src/views/starting/components/ScanStatusLabel.tsx`

## Goal

Introduce `const palette = useAppPalette();` where it's not already present,
rewrite every `darkMode ? A : B`, and stop reading `darkMode` from the store
in these views.

## Tokens most useful here

- `palette.textPrimary`, `palette.textSecondary`, `palette.textMuted`
- `palette.surfaceBg`, `palette.surfaceCard`, `palette.surfaceSubtle`
- `palette.border`, `palette.borderStrong`, `palette.divider`
- `palette.accent`, `palette.accentSurface*`, `palette.accentBorder*`,
  `palette.accentTextStrong` (for "Continue manually →" links and accent
  banners)
- `palette.statusInfoSurface`, `palette.statusInfoBorder`,
  `palette.statusInfoText` (for "scanning..." banners)
- `palette.statusSuccess`, `palette.statusWarning` (detection states)
- `palette.shadowMd`, `palette.shadowLg`

## Pitfalls

- `StartingView.tsx` uses a translucent backdrop
  `rgba(26, 26, 26, 0.95) : rgba(250, 250, 252, 0.85)` that does not map to a
  palette surface cleanly. Keep literal + `palette.isDark` and a
  `TODO(style-migration)` comment.
- `FindingRobotView.tsx` passes a `darkMode` prop into `ConnectionCard` and
  similar child components defined in-file. Keep the prop on those local types
  (internal to the file) but read from palette first.

## Definition of done

- `grep -n "darkMode ?" <bucket-files>` returns 0 results (except for the
  intentional TODO in `StartingView.tsx`).
- No `const darkMode = useAppStore((s) => s.darkMode);` remains in the bucket
  files.
- `./scripts/validate-style-migration.sh` on the bucket scope is green.
- `npm run typecheck` + `npx eslint --fix <files>` clean.
