/*
DEPRECATED / UNSUPPORTED

Lakehouse SQL endpoint DML activation is retired for this repository.
Use the existing Fabric notebook item with CONTROL_ONLY_PROMOTION=true
and the documented run payload in `.azure/notebook-run-v120-readiness.json`.
*/

THROW 51000, 'Unsupported operation: SQL endpoint force activation is disabled. Use Fabric notebook control-only promotion runbook (Section 18).', 1;
