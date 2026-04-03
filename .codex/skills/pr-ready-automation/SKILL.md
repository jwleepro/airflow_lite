---
name: pr-ready-automation
description: Define or implement draft pull request promotion rules for this repository, including required CI checks, blocking labels, review-state automation, and GitHub Actions workflow wiring. Use when Codex needs to decide when a draft PR should become ready for review automatically or inspect why the promotion did not happen.
---

# PR Ready Automation

Treat `ready for review` as a review gate, not a merge gate.

## Workflow

1. Read `AGENT.md`, `PLAN.md`, and `PROGRESS.md` first.
2. Inspect `.github/workflows/`, branch protection assumptions, and any existing PR labels before defining new gates.
3. Keep the ready policy narrower than merge policy: require reviewable quality, not final approval.
4. Prefer a small set of deterministic inputs such as CI success, draft state, and blocking labels.
5. Add one explicit operator override when ambiguity matters, such as a `ready:auto` label.
6. Document the policy in repository docs and keep any local Codex command or agent references aligned.

## Default Policy Shape

- Require a draft PR.
- Require the minimal required CI checks for review readiness.
- Reject PRs with blocking labels such as `blocked` or `wip`.
- Use labels or PR metadata instead of parsing free-form comments when possible.
- Avoid conditions that can only be satisfied after review has already started.

## Focus Areas

- GitHub Actions trigger selection
- required check naming and stability
- label-based opt-in or opt-out behavior
- draft-to-ready transitions without noisy loops
- clear operator-facing documentation

## Do Not Use

Do not use for generic merge policy, release automation, or non-GitHub review workflows.
