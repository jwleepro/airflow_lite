# PR Ready Automation Policy

## Purpose

This document records the repository-level findings and working policy for automatically promoting draft pull requests to `ready for review`.

Use this reference when an agent needs to:

- define or update GitHub Actions for draft-to-ready transitions
- choose the minimum required CI checks for review readiness
- inspect why a PR did not auto-promote
- coordinate local Codex assets related to PR readiness

## Current Findings

### Review State Semantics

- Treat `ready for review` as a review gate, not a merge gate.
- A PR can become ready before it has human approval.
- Conditions that are only satisfiable after review has started should not be part of the ready gate.

### Repository CI Baseline

At the time of the initial policy design, the repository had no general-purpose CI workflow for pull requests. The visible repository automation workflows were not baseline test or lint gates.

The practical minimum CI candidates identified for this repository were:

1. `smoke`
   - command: `python -m compileall src/airflow_lite`
   - purpose: fail fast on syntax and basic import errors
2. `unit-core`
   - command: `pytest tests/test_alerting.py tests/test_api.py tests/test_backfill.py tests/test_engine.py tests/test_extract.py tests/test_mart.py tests/test_reference_reader.py tests/test_scheduler.py tests/test_service.py tests/test_settings.py tests/test_storage.py -q -p no:cacheprovider -m "not integration"`
   - purpose: cover the main code paths without requiring live Oracle access
3. `integration-oracle`
   - command: `pytest tests -m integration --run-integration -q`
   - purpose: validate live Oracle behavior separately from normal PR readiness

### Required Check Recommendation

The recommended initial required checks for automatic promotion are:

- require `smoke`
- require `unit-core`
- do not require `integration-oracle` for normal PR readiness

`integration-oracle` is better suited to manual execution or a scheduled workflow because the repository already separates integration tests behind the `--run-integration` flag.

### Ready Gate Recommendation

The recommended default policy for this repository is:

1. PR is currently `draft`
2. required checks are successful
3. PR does not have blocking labels such as `blocked` or `wip`
4. an explicit operator intent signal exists when ambiguity matters, preferably a `ready:auto` label

This keeps the ready gate stricter than "push anything" but lighter than merge approval.

### Environment Findings From 2026-04-02 Investigation

The follow-up investigation for PR `#1` on branch `codex/default-draft-pr-workflow` established these repository and tool constraints:

- the repository currently has no `.github/workflows/` directory, so there is no server-side workflow that can evaluate or promote draft PRs yet
- the local environment used by Codex did not have `gh` installed, so local CLI-based PR state changes were not available
- the connected GitHub tooling available in this session exposed PR metadata and comments, but not a direct draft-to-ready mutation
- the open draft PR `#1` had no successful commit statuses on head commit `a5be6e0acd0ad2e7c5a8b3ce54868e257033866a`
- the same PR also had review comments requesting changes, so it did not satisfy the working ready policy even if a state-change API had been available

Practical implication: automatic promotion should be implemented as a GitHub-side workflow, not as a local-only Codex action.

### Implemented Workflow Shape

The repository now implements the ready gate inside the `PR Checks` GitHub Actions workflow at `.github/workflows/pr-checks.yml`.

That workflow contains three stable jobs:

1. `smoke`
   - runs `python -m compileall src/airflow_lite`
2. `unit-core`
   - runs the repository's non-integration pytest set
3. `draft-pr-ready-gate`
   - runs only for draft PRs
   - requires both `smoke` and `unit-core` to succeed in the same workflow run
   - requires the `ready:auto` label
   - rejects PRs carrying `blocked` or `wip`
   - uses GitHub GraphQL `markPullRequestReadyForReview` to promote the PR

This implementation deliberately keeps the ready gate in the same workflow instead of chaining a second workflow from `workflow_run`. GitHub documents that `workflow_run` only becomes active when the workflow file already exists on the default branch, so a same-PR rollout would not be reliable if the repository tried to split the gate into a separate workflow immediately.

### Recommended Automation Sequence

Use this order when implementing or extending draft-to-ready automation:

1. confirm the ready policy and stable required check names
2. address review blockers and make sure required tests or smoke checks can actually run
3. add the GitHub Actions workflow that evaluates the deterministic gate
4. trigger the workflow again with a fresh PR event such as `push`, `synchronize`, or label changes to validate the automation on an existing draft PR

The workflow can be created after the review-remediation work is complete. In this repository that is safer than creating the workflow first, because the check names and blocking conditions are still being established.

## Local Codex Assets

The repository-local Codex assets for this workflow are:

- agent: `.codex/agents/github-automation-agent.toml`
- skill: `.codex/skills/pr-ready-automation/`

Use them with this division of responsibility:

- `github-automation-agent`: implement or update GitHub Actions, labels, and PR state automation
- `pr-ready-automation`: design or revise the repository policy before touching workflows
- `review-agent`: verify whether unresolved review findings or risk items should keep the PR in draft
- `test-agent`: confirm that the required validation commands are runnable and stable enough to be used as ready checks

If PR review comments must be converted into concrete implementation tasks first, the GitHub plugin skill `github:gh-address-comments` is the preferred companion workflow.

## Implementation Guidance

When implementing or revising the GitHub workflow:

1. keep the ready policy deterministic
2. prefer labels and check names over parsing free-form comments
3. keep check names stable so branch protection and automation do not drift
4. avoid auto-promotion loops triggered by repeated workflow events
5. document the final policy in both repository docs and local Codex references
6. prefer GitHub-hosted state transitions over local CLI-only steps when the goal is unattended automation
7. if the repository later splits checks and promotion into separate workflows, re-check the default-branch limitations on `workflow_run` before relying on chained execution

## Scope Boundary

This document is about repository-specific Codex and GitHub workflow policy.

Do not use it for:

- application business logic
- analytics API behavior
- Oracle extraction semantics
- generic GitHub advice that is not specific to this repository
