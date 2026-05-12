# Bucket 5 - Controller + sliders

> Read [`_shared-context.md`](./_shared-context.md) first.

## Scope (5 files, ~33 ternaries)

- `src/views/active-robot/controller/Controller.tsx` (5)
- `src/views/active-robot/controller/components/Joystick2D.tsx` (5)
- `src/views/active-robot/controller/components/SimpleSlider.tsx` (9)
- `src/views/active-robot/controller/components/CircularSlider.tsx` (9)
- `src/views/active-robot/controller/components/VerticalSlider.tsx` (5)

Do not touch any other file.

## Goal

All five files already have `useAppPalette()` imported and a header comment
`// TODO(style-migration): finish migrating remaining darkMode ternaries.`
Finish the migration, remove the alias, drop the TODO.

## Tokens most useful here

- `palette.accent`, `palette.accentSurface`, `palette.accentSurfaceHover`,
  `palette.accentSurfaceActive`, `palette.accentBorder`,
  `palette.accentBorderStrong`, `palette.accentGlow`, `palette.accentGlowSoft`,
  `palette.shadowAccent`
- `palette.textPrimary`, `palette.textMuted`, `palette.textFaint`
- `palette.border`, `palette.borderStrong`, `palette.divider`
- `palette.surfaceCard`, `palette.surfaceSubtle`
- `ACCENT.main` from `@styles/tokens` for static accent borders where the
  accent stays the same in both modes.

## Pitfalls

- The sliders build subtle inner shadows with accent tints. Use
  `palette.accentGlowSoft` instead of open-coding `rgba(255, 149, 0, 0.15)`.
- Thumb / track contrast in dark mode uses `whiteAlpha(0.5)` and
  `blackAlpha(0.3)`-style values. Prefer `palette.border` /
  `palette.borderStrong` where the semantic fits, fall back to the alpha
  helpers only when needed.

## Definition of done

- `grep -n "darkMode ?" src/views/active-robot/controller/` returns nothing.
- No `const darkMode = palette.isDark;` remains in bucket files.
- `./scripts/validate-style-migration.sh src/views/active-robot/controller/`
  is green.
- `npm run typecheck` + `npx eslint --fix <files>` clean.
