# Handoff

Executor: dedicated central-database conversation `019f5c2a-859e-7ed2-8ecf-e94b84f454cb`.

The manager releases one lane at a time in the frozen queue order and records immutable callbacks.
The first lane opens only after this packet is committed, pushed, and independently accepted.
