# Style migration briefs

One file per bucket - each is a ready-to-paste prompt for an autonomous agent
(Cursor, Claude Code, etc.). Buckets are **disjoint** so multiple agents can
work concurrently without conflicts.

## How to use

Pick a bucket file below, copy its entire contents into a fresh agent session,
and let it run. Do not combine buckets in a single session.

Before picking, run the dashboard to see live per-bucket progress:

```bash
cd reachy_mini_desktop_app
./scripts/style-migration-status.sh
```

| Bucket | File | Est. ternaries | Tip |
|---|---|---|---|
| 1 - LogConsole | [`bucket-1-logconsole.md`](./bucket-1-logconsole.md) | 39 | Local file set - safest first bucket |
| 2 - Application store | [`bucket-2-application-store.md`](./bucket-2-application-store.md) | 101 | Largest bucket; uses mostly text/surface/border tokens |
| 3 - Finding robot + setup | [`bucket-3-finding-setup.md`](./bucket-3-finding-setup.md) | 85 | Touches several views, all disjoint from buckets 4/5/6 |
| 4 - Active robot shell + right panel | [`bucket-4-active-robot-shell.md`](./bucket-4-active-robot-shell.md) | 57 | Does NOT touch application-store files (bucket 2) |
| 5 - Controller + sliders | [`bucket-5-controller.md`](./bucket-5-controller.md) | 33 | All siblings under `controller/` |
| 6 - Shared components + cleanup | [`bucket-6-shared-cleanup.md`](./bucket-6-shared-cleanup.md) | 18 + cleanup | Small files, easy win to close the migration |

## Shared contract (every bucket follows this)

1. Read `src/styles/MIGRATION_GUIDE.md` first. The mapping tables answer 95% of
   questions.
2. Read `src/styles/MIGRATION_STATUS.md` for global context and palette tokens
   available (sections 2.b / 2.c / 2.d of the guide).
3. Reference implementations (do not modify them):
   - `src/components/emoji-grid/EmotionWheel.tsx` (best reference)
   - `src/views/active-robot/right-panel/expressions/ExpressionsSection.tsx`
   - `src/components/viewer3d/SettingsOverlay.tsx`
4. Run `./scripts/validate-style-migration.sh <bucket-files>` before AND after
   - abort if "before" is red (someone else broke something).
5. Do not modify any file outside the bucket's file list.
6. Do not add new palette tokens. If you need one, stop and escalate.
7. Keep public `darkMode` props: mark them `@deprecated`, remove from
   destructuring, but keep them in the `Props` interface so callers compile.
