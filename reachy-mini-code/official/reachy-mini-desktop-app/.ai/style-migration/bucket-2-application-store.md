# Bucket 2 - Application store

> Read [`_shared-context.md`](./_shared-context.md) first.

## Scope (6 files, ~101 ternaries + 2 TODO files)

Migration:

- `src/views/active-robot/application-store/discover/Section.tsx` (35)
- `src/views/active-robot/application-store/installed/InstalledAppsSection.tsx` (30)
- `src/views/active-robot/application-store/installation/Overlay.tsx` (23)
- `src/views/active-robot/application-store/discover/Modal.tsx` (13)

Review (keep bespoke colors, but re-check they still need a `TODO` comment
after the new palette tokens landed):

- `src/views/active-robot/application-store/discover/components/SearchBar.tsx`
  (private purple `#8b5cf6` - leave with TODO if still needed)
- `src/views/active-robot/application-store/discover/components/AppCard.tsx`
  (private purple + web indigo - same)

Do not touch any other file, including `modals/CreateAppTutorial.tsx`.

## Goal

Every listed file already has `useAppPalette()` imported and a header comment
`// TODO(style-migration): finish migrating remaining darkMode ternaries.` plus
a temporary alias `const darkMode = palette.isDark;`.

For each file:

1. Replace each `darkMode ? A : B` with the right semantic token (see the
   tokens list in `_shared-context.md`).
2. Remove the alias `const darkMode = palette.isDark;` when no reader remains.
3. Remove the `// TODO(style-migration): finish migrating remaining darkMode
   ternaries.` comment.

## Tokens most useful here

- `palette.textSecondary`, `palette.textMuted`, `palette.textFaint`,
  `palette.textPrimary`
- `palette.surfaceCard`, `palette.surfaceCardHover`, `palette.surfaceSubtle`,
  `palette.surfaceBg`
- `palette.border`, `palette.borderStrong`
- `palette.accent`, `palette.accentSurface`, `palette.accentSurfaceHover`,
  `palette.accentSurfaceActive`, `palette.accentBorder`,
  `palette.accentBorderStrong`, `palette.accentTextStrong`
- `palette.statusSuccess`, `palette.statusError` (install states)
- `palette.shadowSm`, `palette.shadowMd`, `palette.shadowLg`

## Pitfalls

- `AppCard.tsx` and `SearchBar.tsx` use `#8b5cf6` (private app purple) and
  `#6366f1` (web app indigo) - these are distinct brand colors, not palette
  tokens. Keep them literal with a `TODO(style-migration)` explaining why.
- Some `darkMode ? '#aaa' : '#666'`, `'#888' : '#999'`, `'#555' : '#bbb'`
  patterns are everywhere. See section 2.d of the migration guide for the
  mapping (`textSecondary` / `textMuted` / `textFaint`).

## Definition of done

- `grep -n "darkMode ?" src/views/active-robot/application-store/` shows only
  files outside this bucket (SearchBar/AppCard TODOs may keep `palette.isDark`
  branches - that's fine).
- Migrated files no longer contain `const darkMode = palette.isDark;`.
- `./scripts/validate-style-migration.sh src/views/active-robot/application-store/`
  is green.
- `npm run typecheck` + `npx eslint --fix <files>` clean.
