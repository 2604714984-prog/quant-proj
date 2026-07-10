# Deterministic rework required

The first green gate and Luna acceptance are superseded. A bounded read-only
audit found two concrete implementation gaps:

1. execution was not bound to a clean committed worktree, so dirty
   implementation code could run under the declared HEAD/HG commit;
2. a nonzero BaoStock `logout()` return code was not treated as failure and
   could allow publication.

These are deterministic Luna rework items, not Sol evidence escalation. No
provider execution or product/research-state change is authorized.
