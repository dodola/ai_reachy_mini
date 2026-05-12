# Shared context (auto-prepended to every bucket prompt)

> This is a style migration task. Read everything below before touching any
> file.

## Your goal

Rewrite every `darkMode ? A : B` ternary in the listed files as a semantic
palette read (`palette.textSecondary`, `palette.statusErrorSurface`, etc.).
Stop branching on `darkMode` for anything a semantic token can express. Keep
the component APIs stable.

## Required reading (IN THIS ORDER)

1. `src/styles/MIGRATION_GUIDE.md` - the mapping cheat-sheet.
   Especially sections:
   - `2. Mapping table` (core tokens)
   - `2.b Status surfaces` (toasts, alerts, badges)
   - `2.c Destructive "danger" buttons`
   - `2.d Neutral greys`
2. `src/styles/MIGRATION_STATUS.md` - global state and bucket ownership.
3. `src/styles/palette.ts` - every available token, documented.

## Reference implementations (read; do NOT modify)

These files are fully migrated and represent the target style. Mimic them.

- `src/components/emoji-grid/EmotionWheel.tsx`
- `src/views/active-robot/right-panel/expressions/ExpressionsSection.tsx`
- `src/components/viewer3d/SettingsOverlay.tsx`
- `src/components/Toast/Toast.tsx` (status surfaces usage)
- `src/components/viewer3d/settings/SettingsCacheCard.tsx` (danger usage)

## Available tokens (quick cheat-sheet)

From `src/styles/tokens.ts`:

- `ACCENT.main | light | dark`
- `STATUS.success | error | warning | info | neutral`
- `DANGER.light | dark`
- `RADIUS.xs | sm | md | lg | xl | xxl | pill | circle`
- `DURATION.instant | fast | base | medium | slow | slower`
- `EASING.standard | spring | entrance | exit`
- `Z.base | raised | dropdown | sticky | overlay | modal | tooltip | notification`
- helpers: `accentAlpha(a)`, `blackAlpha(a)`, `whiteAlpha(a)`, `hexToRgba(hex, a)`, `transition(...)`

From `useAppPalette()` (dark/light aware):

- Accent: `accent`, `accentLight`, `accentDark`, `accentTextStrong`,
  `accentSurface`, `accentSurfaceHover`, `accentSurfaceActive`, `accentBorder`,
  `accentBorderStrong`, `accentGlow`, `accentGlowSoft`
- Text: `textPrimary`, `textSecondary`, `textMuted`, `textFaint`, `textDisabled`
- Surface: `surfaceBg`, `surfaceCard`, `surfaceCardHover`, `surfaceSubtle`
- Border: `border`, `borderStrong`, `divider`
- Overlay: `overlayScrim`, `overlayScrimStrong`
- Shadow: `shadowSm`, `shadowMd`, `shadowLg`, `shadowAccent`
- Status (base): `statusSuccess`, `statusError`, `statusWarning`, `statusInfo`,
  `statusNeutral`
- Status (tinted tiles): `status{Success,Error,Warning,Info,Neutral}Surface |
  Border | Text` + `statusErrorSurfaceHover`
- Danger: `dangerText`, `dangerBorder`, `dangerSurfaceHover`
- Ghost: `ghostBg`, `ghostBorder`
- Flag: `isDark` (branch on this **only** if no semantic token fits)

## Rules of thumb

1. `const darkMode = palette.isDark;` is a temporary alias. Replace usages
   with the palette token, then delete the alias at the end. Do not ship it.
2. If a file has `// TODO(style-migration): finish migrating remaining
   darkMode ternaries.`, remove that comment once done.
3. If you genuinely cannot map a value to a token (custom hex, bespoke
   gradient), keep the literal but:
   - Still read `palette = useAppPalette()` (never `darkMode` from the store).
   - Branch on `palette.isDark`, not on a local `darkMode` prop.
   - Leave a `// TODO(style-migration): <one-line reason>` comment.
4. Never add fields to `palette.ts` yourself - if a pattern truly recurs, stop
   and ask. Don't invent tokens inside the bucket.
5. Never remove `darkMode` from a component's `Props` interface. Mark it
   `@deprecated`, stop destructuring, drop from body. Callers stay green.

## Validation workflow

Before starting, inspect the dashboard (shows ternary count per bucket) and
validate the bucket's current state:

```bash
cd reachy_mini_desktop_app
./scripts/style-migration-status.sh          # dashboard
./scripts/validate-style-migration.sh <bucket-files>
```

If "before" is red (typecheck fail or hardcoded accent), stop and report.

After finishing each file:

```bash
npm run typecheck
npx eslint --fix <files-you-touched>
```

Before declaring the bucket done:

```bash
./scripts/validate-style-migration.sh <bucket-files>
# Should show 0 darkMode ternaries in your bucket.
```

## Output

When finished, print:

- Files touched (count + paths).
- Ternaries before vs after.
- Any TODO(style-migration) intentionally left behind (with one-line reason
  each).
- `validate-style-migration.sh` status.
