# Managed recovery pilot foundation

This release adds an authenticated loopback control service and a runner to the real synthetic PostgreSQL exercise. It is **not a paid deployment or production multi-tenant service**. No customer, recovery stack, fee, signed terms or written access authorization has been supplied. All examples remain customer-neutral and synthetic.

## End-to-end demonstration

Requires the PostgreSQL prerequisites in [recovery.md](recovery.md).

```sh
python -m vendor_assurance.managed_demo --output output/managed-demo
```

This provisions four random bearer credentials, starts a loopback HTTP service, denies requester self-approval and premature runner execution, approves and claims the job, executes a real restore, denies runner self-acceptance, and records a simulated reviewer decision. It removes demo credentials/state and closes the service. `managed-demo.json` explicitly marks `review_simulated=true`. The single demo process holds all roles for testing; this is not separation of real people.

## Manual role workflow

```sh
python -m vendor_assurance.managed init --state output/control-state
python -m vendor_assurance.managed serve --state output/control-state
```

In another terminal, create a job with the requester token file. Only one fixed synthetic adapter is accepted.

```sh
python -m vendor_assurance.managed create --token-file output/control-state/requester.token
```

Use the returned ID in these commands, replacing `JOB_ID`:

```sh
python -m vendor_assurance.managed approve --id JOB_ID --token-file output/control-state/approver.token
python -m vendor_assurance.managed execute --id JOB_ID --token-file output/control-state/runner.token --output output/managed-run
python -m vendor_assurance.managed read --id JOB_ID --token-file output/control-state/reviewer.token
```

After inspecting the result, replace `RESULT_SHA256` with the returned digest and write your actual review rationale:

```sh
python -m vendor_assurance.managed accept --id JOB_ID --token-file output/control-state/reviewer.token --result-sha256 RESULT_SHA256 --rationale 'Reviewed the scoped exercise evidence'
```

Use `reject` instead of `accept` when evidence does not support acceptance. Failed exercises cannot be accepted. Real operators must each hold only their authorized credential; bootstrap currently creates demonstration identities, not SSO identities.

Revoke job execution using the approver credential:

```sh
python -m vendor_assurance.managed revoke --id JOB_ID --token-file output/control-state/approver.token
```

The local state-directory owner can revoke a credential without an HTTP administrator endpoint:

```sh
python -m vendor_assurance.managed disable-credential --state output/control-state --token-file output/control-state/runner.token
```

## Enforced boundaries

- Random 256-bit bearer credentials; only SHA-256 token hashes are stored in SQLite. Token files are mode 0600 inside a mode 0700 directory. Tokens must never be committed or printed.
- Server-derived tenant and role; callers cannot choose them in a request. Scoped job lookup and transactional claims prevent cross-tenant reads and duplicate claims.
- Requester, approver, runner and reviewer roles, with distinct actor requirements for approval and acceptance.
- Fixed synthetic adapter, no arbitrary shell command, production resource, backup path or cloud spending request accepted.
- Fifteen-minute authorization expiry, a 120-second execution budget, two local clusters per exercise, and fixed recovery/data-age objectives.
- Cooperative runner checks before database commands, with a five-second subprocess timeout in managed mode. Revocation, service unavailability or budget exhaustion fails closed at the next check. Cleanup bypasses cancellation to stop resources.
- Evidence digest binding and immutable final review transitions. The service also checks successful cleanup, application checks, scenario and numeric objectives before allowing review.

The execution budget is a cooperative deadline, not a kernel-enforced process, disk or CPU quota. An in-flight command, a control request (10-second timeout), and cleanup can exceed the budget. Multiple jobs are not globally capacity-limited. Cloud spend is excluded by the fixed local adapter, not measured through a billing API.

## Trust and operating limits

The runner is trusted to report truthfully; authentication proves possession of its credential, not source accuracy. Bearer credentials do not establish that a human is physically present. The local administrator can modify SQLite and credentials. Records are neither independently signed nor immutable audit storage. Key rotation, enterprise identity, TLS, rate limits, durable scheduling, hard resource quotas, HA, customer connectors and external evidence storage remain production gates.

The HTTP service binds only to 127.0.0.1, rejects browser-origin requests and limits body size; do not expose it via tunnels, reverse proxies or a public interface. It is a pilot CLI service, not a browser reviewer portal. Local processes with token access can act as that role. Protect the state directory and OS account accordingly.

If the runner is revoked/expired, its final submission may also be denied. Local recovery evidence still exists; an approver must inspect cleanup. Crashed jobs are not automatically retried; reads expose expired authorization/runtime and the operator must investigate remaining resources. There is no automatic refund, invoicing, procurement, customer outreach or renewal execution.

## Customer deployment prerequisites

Complete [the paid pilot worksheet](paid-pilot-worksheet.md). Implement and evaluate the selected customer adapter only after its stack and authorized resources are known. Use a protected nonproduction environment and the customer's existing recovery mechanism. Compare the customer workflow with its configured incumbent before claiming differentiation or savings.
