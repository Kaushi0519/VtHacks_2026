# `ishan/` — my workspace

- [`Ishan.MD`](Ishan.MD) — my role, ownership, and task plan.

## How I avoid merge conflicts: one branch per task

Every task gets its own short-lived branch off a freshly pulled `main`, and merges back the same day.

```bash
git checkout main && git pull --rebase         # always start from the latest main
git checkout -b demo/<task>                    # e.g. demo/i2-scenario-pacing
# ...work, small commits...
git checkout main && git pull --rebase         # pick up what teammates merged meanwhile
git merge demo/<task> && git push origin main
git branch -d demo/<task>
```

Why this works: a conflict only happens when two people change nearby lines of the same file and
both sit unmerged for a while. Small branches merged the same day keep that window tiny.

When a task touches a file someone else owns (see "Repo map & ownership" in `../CLAUDE.md`, and the
"conflict-prone shared files" list), I also:

1. say so in the team chat before editing,
2. keep the change as small and additive as possible,
3. get a quick look from the owner (Person 1 for contracts) before merging.

If a conflict does happen on a lockfile: take theirs, then re-run `uv sync` / `npm install`.
