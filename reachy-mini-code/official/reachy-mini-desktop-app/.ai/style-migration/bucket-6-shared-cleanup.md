# Bucket 6 - Shared components + cleanup

> Read [`_shared-context.md`](./_shared-context.md) first.

## Scope (7 files)

Active migration:

- `src/components/Toast/Toast.tsx` (4 - status surfaces usage; use
  `palette.status{Success,Error,Warning,Info}Surface|Border|Text`)
- `src/components/viewer3d/Scene.tsx` (3)
- `src/components/viewer3d/Viewer3D.tsx` (1)

Already at 0 (run `./scripts/style-migration-status.sh` to confirm - just
do a final pass on these to remove any stale `@deprecated darkMode` props if
the agent left them behind):

- `src/components/FPSMeter.tsx`
- `src/components/FullscreenOverlay.tsx`
- `src/components/DevPlayground.tsx`
- `src/components/AppTopBar.tsx`

Also run a sanity pass on these already-cleaned files (should stay at 0):

- `src/components/viewer3d/settings/SettingsCacheCard.tsx`
- `src/components/viewer3d/settings/SettingsResetCard.tsx`
- `src/components/viewer3d/settings/SettingsDaemonCard.tsx`
- `src/components/viewer3d/settings/ChangeWifiOverlay.tsx`

## Goal

Finish migrating the shared low-level components. Most receive `darkMode` as a
prop from many callers - **keep the prop**, mark it `@deprecated`, and read
from `useAppPalette()` inside.

## Tokens most useful here

- `palette.textMuted`, `palette.textFaint`, `palette.textDisabled`
- `palette.border`, `palette.divider`
- `palette.surfaceCard`, `palette.surfaceSubtle`, `palette.surfaceBg`
- `palette.shadowSm`, `palette.shadowMd`, `palette.shadowLg`,
  `palette.overlayScrim`, `palette.overlayScrimStrong`

## Pitfalls

- `FullscreenOverlay.tsx` is imported by many buckets. Do NOT remove the
  `darkMode` prop from its public `Props` interface. Mark it `@deprecated`
  and stop destructuring it; read `palette.isDark` internally only where a
  truly bespoke value is required.
- `Viewer3D.tsx` has a `resolveBackground(backgroundColor, darkMode)` helper
  (pure function). You can either:
  - Pass `palette.isDark` where the helper is invoked, OR
  - Leave the helper as-is (it's the only remaining ternary) - not blocking.
- `Scene.tsx` (Three.js) and `applyRobotMaterials.ts` (pure util) receive
  `darkMode` as a prop/arg from their parent. **Do not** migrate those files
  - they require a refactor of the Three.js call sites. They are explicitly
  out of scope for now.

## Cleanup: confirm resolved TODOs

Run `grep -rn "TODO(style-migration" src` and verify the following TODOs are
**gone** (they were resolved in the palette extension pass):

- `SettingsCacheCard.tsx` / `SettingsResetCard.tsx` (danger red)
- `SettingsDaemonCard.tsx` (neutral stopped grey)
- `ChangeWifiOverlay.tsx` (accent text)
- `Toast.tsx` (status surfaces)

Remaining TODOs are intentional - see `MIGRATION_STATUS.md` "Leftover TODOs".

## Definition of done

- `grep -n "darkMode ?" <bucket-files>` returns at most 1 result (the
  Viewer3D helper if you chose to leave it).
- `FullscreenOverlay.tsx` Props still includes `darkMode?: boolean` with
  `@deprecated` tag.
- `./scripts/validate-style-migration.sh` reports < 5 total ternaries
  workspace-wide (ideally 0 outside `applyRobotMaterials.ts` and `Scene.tsx`).
- `npm run typecheck` + `npx eslint --fix <files>` clean.
