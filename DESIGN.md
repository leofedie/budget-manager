# Design rationale

The project separates the CLI, services, validation, transaction model and CSV
storage so that financial calculations can be tested without terminal input or
file access. New transactions and imported rows share the same validation rules,
preventing invalid records from reaching the reporting layer. CSV is readable,
portable and appropriate for a first release without an external database.
Writing to a temporary file before replacing the active CSV protects the previous
file from a failed write before replacement. The trade-off is a simple,
single-user architecture rather than a concurrent transactional system.
