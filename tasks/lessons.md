# Lessons Learned

This file is updated after every correction. Review it at the start of each session.

---

## Dialog Placement
**Mistake**: Placed `<Dialog>` inside `<Tabs>` between `<TabsContent>` elements.
**Rule**: Dialog (and any portal-based component) must be a sibling of the main content wrapper — never a child of `<Tabs>`. Always render it after `</Tabs>` and before the outermost closing `</div>`.

## Migration JSONB Import
**Mistake**: Importing `JSONB` from `sqlalchemy.dialects.postgresql` at the top of a migration file.
**Rule**: Put `from sqlalchemy.dialects.postgresql import JSONB` **inside** the `upgrade()` function body — Alembic runs migrations in isolation and top-level dialect imports can cause environment-specific failures.

## Read Before Edit
**Mistake**: Attempting to edit a file that had been modified since it was last read, causing a tool error.
**Rule**: Always re-read a file immediately before editing it if any time has passed or any other tool has run since the last read. Use the Read tool, not memory.
