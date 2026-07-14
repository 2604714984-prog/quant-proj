# Migration

The cutover is intentionally staged:

1. freeze a read-only inventory of every legacy repository and worktree;
2. build and test the new single repository against temporary data;
3. verify read-only access to the existing central database;
4. move the mutable data root without changing database bytes;
5. replace the old controller checkout with this repository;
6. remove local legacy checkouts only after their remote refs or recovery
   manifests are verified.

Dirty legacy worktrees are never silently discarded. They must be classified as
already preserved, intentionally obsolete, or migrated before deletion.

The 2026-07-15 cutover is complete. Legacy checkouts are retained temporarily at
/home/rongyu/workspace/quant-data/recovery/legacy-local as opaque rollback
material only. Their linked-worktree metadata is not expected to work after the
move. Verified patches, untracked-file archives, remote archive tags, and Git
bundles are recorded in cutover_receipt.json.
