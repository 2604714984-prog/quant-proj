# Historical Model-Routing Reference

Status: `HISTORICAL_ADVISORY`

The former `SOL_MANAGER_LUNA_DELIVERY_V2` policy recorded how earlier work was
routed. It is retained for provenance only. It does not bind new tasks to a
model, role name, thread UUID, callback target, dispatcher, gate manifest, or
duplicate acceptance pass.

Current routine work follows `runbooks/task_dispatch.md`: one issue, one
branch/PR, focused CI, and a short closeout. Agents may be selected according to
availability and task difficulty. Elevated review is chosen by the boundary
being changed, not by this historical routing record.

Existing model-specific configuration files may remain as local preferences;
they are not controller acceptance criteria.
