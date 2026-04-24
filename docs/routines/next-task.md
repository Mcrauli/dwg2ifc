# dxf2ifc — `next-task` routine prompt

> This file is the input for the scheduled Claude agent that advances Plan A
> one task at a time. Invoke via the `schedule` skill. Owner: Lauri Rekola.

## Instructions for the agent

You are continuing the dxf2ifc project from wherever it was left off. **Do one
task and stop.** Never bundle two tasks into a single run — keep each run small
and verifiable.

### 1. Orient yourself

- `git pull --rebase origin master`. If the rebase conflicts, abort with
  `git rebase --abort` and STOP — report the conflict and leave resolution to
  Lauri. Never force-push.
- Read **`PROGRESS.md`** — this is the authoritative volatile state. Its
  "Current task" section names the next task; its "Blockers" section is
  checked next.
- Read the project `CLAUDE.md` for stable context (decisions, Talo2000
  table, YTV findings).
- Read the matching task section in
  `docs/superpowers/plans/2026-04-24-plan-a-core-cli-wall-pipeline.md` —
  it has the failing test, the implementation, and the commit message.

### 2. Check for blockers

If `PROGRESS.md` "Blockers" has any open entry, or the current task carries
a blocker note, STOP. Do not attempt to proceed around it. Report:

```
BLOCKED on Task N: <blocker text>.
No commits made. Handing back to Lauri.
```

### 3. Execute the task

Follow the plan's steps literally — failing test first, implementation
second, passing test, commit. Use the exact commit message from the plan
(append the `Co-Authored-By: Claude Opus 4.7 (1M context)` trailer as in
prior commits).

### 4. Time budget

A single routine run has a soft budget of ~90 minutes of agent work. If you
notice a task is too large to finish in one run:

- **Preferred:** split the task at a logical checkpoint. Commit what works
  with a `WIP(Task N): <subset>` subject. Update the README progress list to
  show `🟡 Task N (partial)`.
- **Never:** commit broken tests or half-applied edits. Revert and STOP if
  you cannot leave the branch in a passing state.

Task 17 (IfcWall + Talo2000 classification) is the likely candidate for a
split — it has both `add_wall` geometry and `add_talo2000_classification`,
and either half can ship on its own.

### 5. Verify before you commit

Before each commit run:

```
Set-Location $HOME\work\dxf2ifc
.venv\Scripts\pytest.exe
.venv\Scripts\ruff.exe check src tests
```

Both must pass. (Task 21 formalises this as a gate; earlier tasks should
still honour it.)

### 6. Update PROGRESS.md

After the commit succeeds, edit `PROGRESS.md`:

- Move the finished task from "Remaining tasks" into the "Completed tasks"
  table with its 7-char short SHA.
- Update "Current task" to point to the next ⏳ task (plan section, first
  step, files to touch, commit subject from the plan).
- Update the "Last synced" timestamp and SHA at the top.
- If you split a task (partial), add a new row labelled `14a`, `14b`, etc.
  to reflect reality and leave the remainder in "Remaining tasks".
- Also bump `README.md`'s header line — "**13/21** tehtävää valmis" — so the
  user-facing status reflects the new count. Do not re-introduce the long
  per-task checklist; `PROGRESS.md` is the source of truth.

Commit these updates with subject `Mark Task N complete in PROGRESS.md`.

### 7. Push

```
git push origin master
```

If the push rejects (someone else committed in parallel), run
`git pull --rebase origin master` and re-push. If the rebase conflicts,
STOP and report; do not force-push.

### 8. Report

End with a one-paragraph summary:

```
Task N (<name>) complete.
Feat SHA: <short SHA of the feat commit>
PROGRESS SHA: <short SHA of the PROGRESS.md commit>
Tests: <X> passed, <Y> warnings.
Next: Task N+1 (<name>).
```

If anything deviated from the plan (a test was rewritten, a dependency
was pinned, etc.), surface it in the summary — do not bury it.

## What NOT to do

- Do not invent new tasks. If you think the plan is wrong, STOP and report.
- Do not skip the failing-test → passing-test discipline. TDD is a hard rule
  for this project.
- Do not merge plans B-F work into Plan A. Out-of-scope work STOPS with a
  report.
- Do not push to a branch other than `master`. Direct pushes to `master` are
  allowed and expected here per the user's stated workflow.
- Do not modify `docs/superpowers/plans/*.md` except to tick boxes if you
  want (cosmetic, optional). The plan's content is authoritative.

## When Plan A is complete

After Task 21 passes:

1. Tag the repo: `git tag -a v0.1.0-plan-a -m "Plan A complete"` and push
   the tag.
2. Update `README.md`'s milestone table to show Plan A ✅ and set
   `PROGRESS.md`'s "Current task" to `Plan A complete — awaiting Plan B`.
3. STOP. Writing Plan B is Lauri's call, not the routine's.
