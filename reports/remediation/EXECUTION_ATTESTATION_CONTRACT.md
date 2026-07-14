# Execution attestation contract

`REMEDIATION_AND_REAUDIT_READINESS_R1` distinguishes two evidence states:

- `MANIFEST_VALID`: the gate JSON, packet, refs, commands, artifacts, and
  declared counts are structurally coherent. This state cannot enter final
  acceptance.
- `EXECUTION_ATTESTED`: a clean result worktree executed the exact packet
  commands; immutable logs and environment identities were recorded; and an
  independent acceptance task replayed the commands and matched the semantic
  output, test count, executable, dependency lock, commit, and tree.

An execution attestation binds the executor task identity and role, exact
command order, executable path and SHA-256, normalized and raw output hashes,
private stdout/stderr logs, exit code, focused-test count, Python/platform
environment identity, dependency-lock identity, and source/result commit/tree.
The logs and attestation are mode `0600` inside the controller task packet.

The creator refuses an existing attestation, an untracked dependency lock, a
dirty worktree, command failure, or test-count drift. The final Luna validator
requires `EXECUTION_ATTESTED`, executes the commands again, and rejects a reused
log, forged count, executable drift, dependency drift, command drift, result
drift, or a shared executor/acceptor task identity.

Historical gates without this evidence remain `MANIFEST_VALID` at most. This
contract does not authorize provider access, data writes, strategy execution,
candidate promotion, or any trading path.
