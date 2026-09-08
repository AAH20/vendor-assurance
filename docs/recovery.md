# Executable PostgreSQL recovery exercise

This extension creates a real PostgreSQL custom-format backup, stops its source, restores into a second disposable cluster, then validates records and commits a new transaction through a loopback HTTP API. All data is synthetic. It never connects to existing PostgreSQL services and ignores ambient PG* connection settings.

## Run

Install PostgreSQL server/client tools and Python 3.12+. `pg_config` must identify the matching binaries including initdb, pg_ctl, pg_dump and pg_restore. Run as an unprivileged OS user with permission to create local PostgreSQL shared memory and bind a loopback port. Do not run as root.

```sh
python -m vendor_assurance.recovery --output output/recovery
A2Z_RECOVERY_INTEGRATION=1 python -m unittest discover -s tests -v
```

The default objectives are 60 seconds recovery time and 300 seconds recoverable data age. Override with `--rto-seconds` and `--rpo-seconds`. All output directories must be new. The CLI exits nonzero for failed exercises, including deliberately failing scenarios.

## Measurement contract

The recovery clock starts after the source cluster stops, before target cluster initialization. It ends after the restored records match and an HTTP write transaction commits and is read back. This includes target initialization, restore, application startup and probes; excludes backup creation, source setup, disaster detection, human mobilization and cleanup. It is not a full organizational outage metric.

Data age is measured from the exercise reference timestamp to the latest restored synthetic committed record, before any post-restore writes. This is a controlled marker measurement, not proof that arbitrary production transactions are complete. Record count and total are checked against the source, not a full database-integrity audit. The small dataset contains three initial orders.

Evidence includes PostgreSQL version, backup hash, restoration artifact hash, timestamped events, checks, measured durations and cleanup status. A passed exercise remains `exercise_passed_pending_human_review`; the program cannot accept on behalf of a customer. Local artifact hashes are not signatures or third-party attestation.

## Failure coverage

- `corrupt_backup`: mutates the dump; integrity mismatch blocks restore.
- `missing_dependency`: stops the restored database; HTTP application check fails.
- `invalid_application`: changes the restored schema; application query fails.
- `stale_data`: restores synthetic records one hour old; the default data-age limit fails.
- `rto_exceeded`: applies an explicitly reported microsecond objective to force the timing gate to fail without artificial sleep.

No incompatible-engine-version, missing-authentication-secret, ransomware-cleanliness, network-partition or cleanup-fault-injection validation is claimed. These are further test requirements for a real deployment.

## Isolation and cleanup

Both clusters use private mode-0700 disposable directories and Unix sockets, with TCP disabled. Local database trust authentication is confined to that directory and the current OS user. The temporary HTTP API binds only to loopback, accepts no input SQL, and has no production credentials. This is process/filesystem isolation, not a malware sandbox; do not restore hostile or customer backups here.

The source is stopped before recovery. Finally the API is closed, database processes are stopped, logs copied, and temporary databases/backups removed. A cleanup failure marks the exercise failed and preserves the workspace path for investigation. Forced process termination or machine failure can bypass Python cleanup; inspect disposable resources after interrupted runs. Do not use this prototype for real sensitive data.

## Next paid pilot gate

Use the existing design-partner package to agree one authorized nonproduction application, acceptance transaction, dependency inventory, timing boundary, evidence retention and cost limit. Establish whether configuring the customer's existing AWS Backup, Veeam, Rubrik or Velero workflow already meets the need. Only then build an adapter to its existing recovery mechanism. No customer has been recruited and no production recovery has been run by this repository.
