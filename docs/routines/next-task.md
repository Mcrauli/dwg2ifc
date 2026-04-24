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
- Read `README.md` — the "Plan A edistyminen" list is the source of truth for
  which task is next. The first `⏳` entry is your task.
- Read the project `CLAUDE.md` for context if you do not already have it.
- Read the matching task section in
  `docs/superpowers/plans/2026-04-24-plan-a-core-cli-wall-pipeline.md` —
  it has the failing test, the implementation, and the commit message.

### 2. Check for blockers

If the next task has a **blocker** comment in the README ("odottaa Lauria:
…" or similar), STOP. Do not attempt to proceed around it. Report:

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

### 6. Update the README progress list

After the commit succeeds, edit `README.md`:

- Change the finished task's `⏳` to `✅` and append the 7-char short SHA.
- Example: `- ✅ Task 14 — \`apply_profile\` mapper (SHA abc1234)`
- If the task was partial, mark it `🟡 Task N — … (partial, SHA abc1234)`
  and leave the next task as `⏳`.

Commit this README update with subject `Mark Task N complete`.

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
SHA: <short SHA of the feat commit>
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
2. Update README's milestone table to show Plan A ✅.
3. STOP. Writing Plan B is Lauri's call, not the routine's.
