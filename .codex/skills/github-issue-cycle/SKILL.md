---
name: github-issue-cycle
description: Repeatedly deliver GitHub issues in milestone order by selecting the next issue, implementing with tests, opening a PR, waiting for CodeRabbit feedback, and applying fixes until completion.
---

# GitHub Issue Cycle

Run a repeatable issue-to-PR loop with milestone and issue-number priority.

## Workflow

1. Discover the active target issue:
   - Check open issues that already have `status:in-progress`.
   - If one or more exist, continue only an issue that is already owned by this run (same branch/worktree or explicit user assignment).
   - If one or more exist but ownership is unclear, stop and report potential overlap instead of selecting a new issue.
   - If none exist, pick the issue with the lowest milestone number, then the lowest issue number inside that milestone.
2. **CRITICAL: Claim the issue IMMEDIATELY before any other work**:
   - Run `gh issue edit <number> --add-label "status:in-progress"` as the FIRST action after selecting an issue.
   - If the label add fails, STOP and report. Do not create a worktree or write code without this claim.
   - After label claim succeeds, try to set GitHub Project item `Status` to `In Progress` when project linkage and permissions allow it.
   - If project status update is unavailable, keep working but leave a kickoff comment that records the failed project-status sync attempt.
   - Post a short kickoff comment with the planned branch, worktree path, and claim timestamp.
3. Create an isolated git worktree per issue (AFTER status is set):
   - Recommended root: `../airflow_lite-worktrees/`
   - Example: `git worktree add -B issue/<issue-number>-<slug> ../airflow_lite-worktrees/issue-<issue-number> origin/main`
   - If the target worktree path already exists and is dirty, do not reuse it for a different issue. Create a clean path instead.
   - Perform all edits, tests, commits, and PR updates inside that issue worktree.
4. Implement the change and add or update tests.
5. Run relevant tests locally and capture results for PR notes.
6. Open a draft PR linked to the issue.
7. Wait for CodeRabbit review, apply requested fixes, and rerun impacted tests.
8. Update PR/issue with verification status and clear active markers:
   - If used, remove `status:in-progress` label.
   - If used, move project `Status` out of `In Progress` (for example `Done`).
   - If status synchronization could not be executed, leave a closeout comment explaining why.
9. After closeout, clean up the issue worktree when safe (`git worktree remove <path>`).
10. Repeat from step 1 for the next issue.

## Operating Rules

- Never start a second issue while another open issue is labeled `status:in-progress`.
- **MANDATORY**: Add `status:in-progress` label BEFORE creating worktree or writing any code.
- If an issue already has `status:in-progress` and is not clearly owned by this run, assume another agent is working on it and do not take it.
- Keep milestone ordering strict: lower milestone number first.
- Keep issue ordering strict within a milestone: lower issue number first.
- Treat `status:in-progress` label claim as the blocking lock.
- Treat project `Status` sync as best-effort secondary sync, and log every failure in issue comments.
- Keep one issue per worktree; do not reuse a dirty worktree across different issues.
- After the worktree is created, do not implement the issue from the main repository checkout.
- Do not skip tests when code changes affect behavior.
- If a blocker appears (CI outage, missing secrets, inaccessible repo), report it in the issue and stop the loop.

## Do Not Use

Do not use this skill for one-off hotfixes, release-only chores, or tasks not tracked in GitHub issues.
