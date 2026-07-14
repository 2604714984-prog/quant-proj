# Research workspace

New strategy research belongs in this repository, but remains separate from the
runtime data layer.

Use these subdirectories as needed:

- definitions/ for outcome-blind strategy specifications;
- reports/ for reproducible research summaries;
- failure-memory/ for rejected specifications and non-retest constraints.

Large outcomes, input snapshots, databases, and provider payloads stay under the
external QUANT_DATA_ROOT. A report may reference their immutable hash but should
not copy the data into Git.

Strategy research must not add broker, paper, live, or automatic trading paths.
Unvalidated work must not be presented as an actionable candidate.
