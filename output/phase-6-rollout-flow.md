# Phase 6 Rollout Flow

## Goal

Create a clean `V3.3` release baseline from Phase 5, then start `phase-6` on top of that baseline.

## Required Preconditions

1. Working tree must be clean.
2. Phase 5 delivery artifacts must exist:
   - `output/delivery-summary-phase-5.md`
   - `output/release-notes-phase-5.md`
3. Release gates must pass:
   - `bash scripts/run-release-gates.sh`

## Recommended Git Flow

1. Review current dirty changes.
   - `git status --short`
2. Split generated noise from real source changes.
   - Exclude cache, build, report, and runtime artifacts from the release commit.
3. Commit the final Phase 5 release baseline on the working branch.
   - Example:
   - `git add <validated files>`
   - `git commit -m "release: Phase 5 delivery baseline (V3.3)"`
4. Create an annotated release tag on that clean commit.
   - `git tag -a v3.3 -m "ClaudeFlow V3.3 Phase 5 release-ready baseline"`
5. Merge the release commit into `main`.
   - `git checkout main`
   - `git merge --no-ff feat/multi-session-runtime-poc -m "merge: Phase 5 release baseline V3.3"`
6. Push branch and tag.
   - `git push origin main`
   - `git push origin v3.3`

## Release Checklist

1. Confirm `git status` is clean before tagging.
2. Confirm `bash scripts/run-release-gates.sh` returns `Passed: 6 / 6`.
3. Confirm `bash scripts/verify-doc-consistency.sh phase-5` passes.
4. Confirm release notes and delivery summary are updated.
5. Confirm `pipeline-state.json` still reports `phase-5.status = accepted`.

## Start Phase 6

After `v3.3` is merged:

1. Create a new working branch from `main`.
   - `git checkout -b feat/phase-6 <main-latest>`
2. Start Super Dev on `phase-6`.
3. Keep Phase 6 changes separate from the `v3.3` baseline.

## Decision Rule

- If the tree is dirty: do not tag, do not merge.
- If the gates fail: fix before tag.
- If the release branch is clean and Gate 1-6 pass: tag `v3.3`, merge to `main`, then begin `phase-6`.
