# Read-only AWS Backup evidence adapter

Implemented integration: official Boto3 `sts:GetCallerIdentity` and `backup:DescribeRestoreJob` for one explicitly authorized RDS instance restore job. There are no list/discovery operations, restore calls, database queries, validation-result writes, resource deletions or role-assumption calls in the adapter. API shape and serialization are tested with Botocore Stubber, not a live AWS account.

The offline reviewer combines preserved restore metadata with an externally supplied application receipt. It does not execute the application validation. No customer-side deployment, permission configuration, paid pilot or live AWS test has occurred.

## Offline demonstration — no SDK or credentials required

```sh
python -m vendor_assurance.aws_backup review \
  --grant examples/aws-backup/grant.json \
  --capture examples/aws-backup/capture.json \
  --application examples/aws-backup/application.json \
  --tenant synthetic-bank --as-of 2026-09-08T12:00:00Z \
  --output aws-review.json
```

All identifiers, authorization references and observations in these fixtures are fictional. The test application digest is a synthetic placeholder, not a shipped Lambda recipe. The result is `eligible_for_human_review`, never customer acceptance. Omit `--application` to demonstrate that AWS job success alone leaves application recovery unverified.

## Authorized collection — prepared, not executed

Install the tested optional SDK in an isolated environment:

```sh
python -m pip install '.[aws]'
```

After written authorization and customer IAM review, the local operator prepares a private grant with tenant, exact account/region, exact current caller ARN, one restore-job ID, source-resource ARN, recovery-point ARN, approved application-test digest, validity window, revocation flag and authorization reference. The live mode must be `authorized`; shipped `synthetic` grants are refused before credential use.

```sh
python -m vendor_assurance.aws_backup collect \
  --grant /private/path/authorized-grant.json \
  --profile CUSTOMER_APPROVED_PROFILE --output /private/path/capture.json
```

The profile is explicitly selected; no secrets are passed in CLI arguments. Boto3 uses its standard profile credential resolution, so review any profile credential provider before use. Configured endpoint URL overrides are ignored. Only commercial AWS regions and RDS instance source ARNs are accepted in this version. Customer IAM must allow the named read operation and must independently constrain access; a local grant is not an IAM policy. Do not grant restore/write permissions for this collector. Validate the applicable AWS resource-level IAM support with the customer rather than assuming the application allowlist is an IAM boundary.

Grant validity is checked before the identity read, before the job read and after the read. The grant file is reloaded between calls, so observed revocation or modification aborts collection. This does not recall data already returned by AWS or cancel an in-flight request. The grant and its authorization reference are operator-maintained assertions, not independently verified written approval. Local administrators can modify them. This CLI is not the authenticated managed-job API.

Output files are exclusive-create, mode 0600. Preserve captures privately: they include customer identifiers, original SDK response metadata and caller identity. The adapter converts SDK datetime objects into UTC ISO strings, preserving their values rather than wire bytes. SHA-256 identifies the serialized response; it is not a signed AWS attestation.

## Interpretation and failure boundaries

AWS restore `Status`, `ValidationStatus` and `DeletionStatus` are checked separately. Missing, failed, pending or timed-out states do not pass. Parent/composite jobs and non-RDS resources are unsupported. Exact source/recovery-point matching is required; older exports missing scope fields fail closed.

The separate application receipt binds the restored target, tenant, job and approved test digest. It must report the restored-record and committed-write checks, PostgreSQL application identity, explicit extra-resource cleanup, an evidence reference, reviewer and ordered timestamps. Those are supplied observations; the adapter does not independently inspect the database engine or validate receipt authenticity. The customer validation recipe, its provenance and its actual runtime remain an integration prerequisite.

Restore duration is **AWS job creation → application validation complete**, including restore and application validation. It excludes outage detection and human mobilization. It differs from the local runner's source-stopped timing boundary and must not be silently mixed into its benchmark. No bridge into that benchmark is claimed.

Recoverable data age uses the application's latest recovered committed transaction relative to restore-job creation. `RecoveryPointCreationDate` is preserved as metadata and is deliberately not substituted for transaction-level recovery evidence. Post-restore writes must not be used as the recovered-data marker. Defaults are 3600 seconds recovery duration, 300 seconds data age and 24 hours capture age; the Python reviewer accepts explicit positive finite overrides. Agree objectives with the customer before applying them.

AWS deletion success applies to the resources represented by that restore test. Additional validation resources require separate cleanup evidence. A receipt asserting their removal does not replace actual collector validation. This module performs no cleanup itself.

## Validation evidence

Tests cover exact request parameters, official SDK response schema/serialization, caller/account/tenant mismatch, changed grants, expiration, malformed scope, independent AWS statuses, missing application checks, mismatched targets/test recipes, invalid chronology and tampered exports. All tests use synthetic data, mocks or Stubber. No comparison against the customer's existing process and no savings claim is established.

Official sources reviewed for this implementation: [DescribeRestoreJob API](https://docs.aws.amazon.com/aws-backup/latest/APIReference/API_DescribeRestoreJob.html), [Boto3 method](https://docs.aws.amazon.com/boto3/latest/reference/services/backup/client/describe_restore_job.html), [AWS restore validation](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html). The write operation used by AWS validation workflows is intentionally absent from this read-only adapter.

Next gate: complete the [paid-pilot worksheet](paid-pilot-worksheet.md), name the customer/application, validate its IAM scope and test recipe, and obtain written authorization before live collection or separately scoped restore execution.
