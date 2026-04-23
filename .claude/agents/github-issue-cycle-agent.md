---
name: github-issue-cycle-agent
description: Milestone-ordered issue delivery with In Progress sync and per-issue worktrees
tools: Read, Grep, Glob, Bash, Edit, Write
model: sonnet
isolation: worktree
---

# GitHub Issue Cycle

Run a repeatable issue-to-PR loop with milestone and issue-number priority.

## Workflow

1. Discover the active target issue:
   - Check open issues that already have `status:in-progress`.
   - If one or more exist, continue the lowest-numbered in-progress issue.
   - If none exist, pick the issue with the lowest milestone number, then the lowest issue number inside that milestone.
2. Activate issue status before coding:
   - First try to set GitHub Project item `Status` to `In Progress` when the issue is connected to a project and permissions allow it.
   - If project status update is unavailable, add `status:in-progress` label as fallback.
   - If both are unavailable due to permissions or missing integration, keep working but leave a kickoff comment that records the failed status-sync attempt.
   - Post a short kickoff comment with the planned branch and worktree path.
3. Create an isolated git worktree per issue:
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
- Keep milestone ordering strict: lower milestone number first.
- Keep issue ordering strict within a milestone: lower issue number first.
- Treat project-status update as primary and `status:in-progress` label as required fallback.
- Status sync should be best-effort and non-blocking, but every failure must be logged in issue comments.
- Keep one issue per worktree; do not reuse a dirty worktree across different issues.
- After the worktree is created, do not implement the issue from the main repository checkout.
- Do not skip tests when code changes affect behavior.
- If a blocker appears (CI outage, missing secrets, inaccessible repo), report it in the issue and stop the loop.

## Do Not Use

Do not use this skill for one-off hotfixes, release-only chores, or tasks not tracked in GitHub issues.
