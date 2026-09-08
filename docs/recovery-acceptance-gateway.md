# Recovery acceptance gateway: synthetic security foundation

The existing loopback managed service now binds authenticated approval and execution to an exact recovery adapter source digest. This is the first gateway increment. It remains a local synthetic pilot, not a customer-hosted RDS service.

## Implemented workflow

1. A provisioned requester creates a fixed synthetic job. The server records the adapter digest and a fifteen-minute expiry.
2. A distinct authenticated approver approves it. A changed adapter requires a new job and approval.
3. A distinct runner claims the job once. SQLite serializes claims; the job stores a unique execution ID and the exact claiming credential hash. Restarting the service does not reset the claim.
4. The runner checks authorization between operations and submits evidence bound to job ID, tenant, execution ID and package digest. Wrong execution scope is rejected without consuming submission.
5. The server computes the review hash over both execution scope and raw report. An independent reviewer must provide that exact hash and a rationale. Evidence integrity is checked again before acceptance. Final review cannot be replayed.

Use the CLI in [managed-pilot.md](managed-pilot.md). For an end-to-end synthetic HTTP demonstration:

```sh
python -m vendor_assurance.managed_demo --output output/gateway-demo
```

The demo runs all roles in one process and **simulates review**. Authenticated role credentials do not establish that four different people participated. Real human review requires separate credential custody and an actual review action.

## Protocol change

`submit` now requires `execution_scope` with the exact `id`, `tenant`, `execution_id`, and `package_sha256` returned by `claim`. `result_sha256` now hashes `{execution_scope, report}`, rather than the raw report alone. Updated CLI and demo supply these fields. Old clients must be updated. Old pending jobs without package binding must be recreated and approved; do not retrofit approval into old records. Previously finalized jobs remain historical records.

## Evaluation

New regression cases cover adapter changes, approver/runner identity separation, credential substitution, scope replay, modified stored reports, concurrent claims, and persistent consumption across database connections. Existing tests retain expiration, revocation, failed cleanup, incorrect metrics, tenant isolation, review hash and independent reviewer checks.

No production security or zero-error guarantee follows from these tests. The [pilot evaluation gates](recovery-assurance-pilot.md) require comparable customer exercises, measured active effort and paid repetition before expansion.

## Remaining boundaries

- Provisioning creates demo principals in one tenant. There is no production IdP/SSO integration or customer enrollment interface.
- HTTP is loopback-only. Do not expose it through a public bind, proxy or tunnel; production transport and deployment isolation are unimplemented.
- Evidence is authenticated at submission by bearer credential, but export hashes are **not signatures**. A trusted runner or local state administrator can fabricate evidence. Signed export provenance and external key custody remain future work.
- The digest covers the adapter source, not the entire host/runtime. No remote attestation exists.
- Execution budgets remain cooperative, not hard OS quotas. Interrupted jobs require operator inspection; a consumed claim is not automatically retried.
- No customer endpoint, arbitrary script, live RDS write probe, exception-management service, or automated outreach is introduced. Customer deployment requires scoped written authorization and further engineering.

OSS implementation and synthetic fixtures are public-facing material. Customer evidence, credentials and negotiated operating commitments remain private. Project owner: [A2Z SOC](https://a2zsoc.com).
