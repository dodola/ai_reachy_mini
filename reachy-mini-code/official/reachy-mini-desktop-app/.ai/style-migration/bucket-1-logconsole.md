# Bucket 1 - LogConsole

> Read [`_shared-context.md`](./_shared-context.md) first.

## Scope (2 files, ~39 ternaries)

- `src/components/LogConsole/index.tsx` (31)
- `src/components/LogConsole/LogItem.tsx` (8)

Do not touch any other file.

## Goal

Wire `useAppPalette()` into both files, drop the local `darkMode` prop reads,
and rewrite every `darkMode ? A : B` using palette tokens. Keep the `darkMode`
prop on `FilterChip` / `LogItem` `Props` but mark it `@deprecated` and stop
destructuring it.

## Tokens most useful here

- `palette.textSecondary`, `palette.textMuted`, `palette.textFaint`,
  `palette.textPrimary`, `palette.textDisabled`
- `palette.border`, `palette.borderStrong`, `palette.divider`
- `palette.surfaceCard`, `palette.surfaceSubtle`
- `palette.statusNeutral` (for the idle chip state)
- `hexToRgba(color, alpha)` if you need a tinted chip background from the
  filter color (the `color` prop the chip already receives).

## Pitfalls

- `FilterChip` currently builds background/border from a dynamic `color` prop
  (`${color}18`, `${color}40`). That is not a `darkMode` ternary - leave it as
  is, or convert to `hexToRgba(color, 0.09)` / `hexToRgba(color, 0.25)` if you
  want stricter types.
- The virtualized list styling (item height, padding) lives in constants - do
  not touch those constants.

## Definition of done

- `grep -n "darkMode ?" src/components/LogConsole/*.tsx` returns nothing.
- `grep -n "darkMode:" src/components/LogConsole/*.tsx` still shows the
  `@deprecated` lines in prop interfaces.
- `./scripts/validate-style-migration.sh src/components/LogConsole/` is green
  with 0 ternaries.
- `npm run typecheck` is green.
- `npx eslint --fix src/components/LogConsole/index.tsx src/components/LogConsole/LogItem.tsx` is clean.
