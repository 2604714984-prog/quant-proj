# External Audit Preflight Fix Response

Date: 2026-07-12

## Issues found while packaging

### Unsafe bulk publication risk

The live workspace contains databases, caches, temporary spill files, provider artifacts, an ignored `.env`, and files over GitHub limits. The response was to publish only review-relevant source/evidence through clean isolated worktrees and to document exclusions.

### Hard-coded workspace paths

The `strategy_work` snapshot contained scripts tied to `/home/rongyu/workspace`. Shared path resolution was introduced through environment-overridable workspace roots, and affected tests were made worktree-aware.

### Frozen-methodology history lookup

A test assumed a changing remote default branch had to remain at an old accepted commit. The implementation now reads the immutable accepted methodology by commit and verifies its content identity.

### GitHub CI dependency drift

The first audit-snapshot CI run failed because `jsonschema` was missing from the workflow installation step. The dependency was added.

### Non-hermetic CI tests

The next CI run showed a shallow checkout could not see the frozen methodology commit and that several tests require separately pinned sibling/external artifacts. Checkout depth was changed to full history. Tests now explicitly skip only when those external artifacts are absent; when present, the original hash and semantic checks still execute.

### Transient GitHub transport failures

Several pushes experienced TLS/time-out failures. Commits remained local and were retried without force. Completion is based on exact remote-ref verification, not on the first push return code.

## Research result impact

None of these fixes changes a strategy definition, return, gate count, source outcome, or adjudication. `strategy_candidate_available=false` remains unchanged.
