/*
DEPRECATED / UNSUPPORTED

Rollback must be performed through the existing Fabric notebook publication
controls and pointer-release invariants. Direct SQL endpoint rollback DML is
disabled for this repository.
*/

THROW 51000, 'Unsupported operation: SQL endpoint rollback script is disabled. Use notebook-led control procedures (Section 18).', 1;
