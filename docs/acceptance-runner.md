# Application recovery acceptance runner

This initial component executes the existing **local synthetic** PostgreSQL exercise under a short-lived, package-bound grant. It does not connect to customer RDS, execute arbitrary scripts, authenticate human approvers, or provide production isolation. The next customer-controlled adapter requires written authorization and separate implementation.

## Run

Requires Python 3.12+ and local PostgreSQL server/client tools. From the repository root:

```sh
mkdir -p output
PYTHONPATH=. python3 examples/acceptance/create_synthetic_grant.py > output/synthetic-grant.json
python3 -m vendor_assurance.acceptance --grant output/synthetic-grant.json --tenant synthetic-bank --output output/acceptance-example
```

Use a fresh output directory for each run. The grant generator names simulated actors and permits only synthetic execution; it does not create actual human approval. Grants expire after ten minutes, with a maximum supported lifetime of fifteen minutes. Changing or revoking the grant during execution prevents review eligibility at subsequent checks. Unknown packages, code digest mismatches, wrong tenants, and expired grants are rejected before adapter execution.

The built-in package creates and restores a disposable database, verifies restored records and a committed HTTP application write, evaluates its recovery objectives, and checks cleanup. Receipts bind tenant, random run ID, executable adapter digest, grant digest, raw report digest, and completion time. Human acceptance remains pending. There is no automatic acceptance or outward communication.

## Evaluation loop

Run `python3 -m unittest discover -s tests -q`. Enable actual database regression exercises with `A2Z_RECOVERY_INTEGRATION=1`; install the optional AWS dependency to include SDK contract tests. The new runner tests cover scope rejection before execution, tenant mismatch, receipt mutation, missing checks, grant lifetime/timezones, and revocation after adapter execution. Existing recovery integration tests exercise underlying restore failure cases.

Freeze the package digest before an exercise. Review every failed or disputed result, add a regression fixture, and approve a new package digest before rerunning. Follow the [pilot KPIs](recovery-assurance-pilot.md) for customer comparisons. No savings or customer acceptance has been established.

## Trust and operational limits

- Grant identities are local assertions. Production identity, independent approval and signed provenance are not implemented here.
- SHA-256 detects accidental or unreconciled changes; anyone able to rewrite the receipt can recompute hashes. `verify` checks consistency, not authenticity or current authorization.
- Authorization files must be controlled by the local operator. No durable one-time grant consumption or replay ledger exists; the grant permits repeated synthetic runs until expiry.
- The 120-second budget is cooperative, checked between operations; cleanup runs independently. It is not a hard process, CPU, storage, or cloud-spend quota. Forced termination may leave disposable resources.
- The package digest covers the recovery adapter source, not Python, PostgreSQL, dependencies, or the host. It is not a software supply-chain attestation.
- Receipt output uses a private directory and mode-0600 receipt; the existing raw report remains within that directory. Customer data must not be used.
- Dependency coverage is limited to the built-in HTTP/PostgreSQL application. No malware-free recovery, regulatory compliance, or zero-error claim is made.

The public schema and runner can evolve in OSS. Customer evidence, credentials, negotiated terms and security architecture belong in private channels agreed with the customer. See [A2Z SOC](https://a2zsoc.com).
