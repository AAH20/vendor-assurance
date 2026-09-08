# Remediation assurance: initial operational extension

This module assesses closure eligibility from normalized, operator-supplied evidence. It does not scan AWS, parse native Prowler exports, inspect GitHub deployments or authenticate people. Examples are synthetic. A production collector and signed evidence exchange remain future work. This is an extension of Vendor Assurance, not a separately deployed product.

## Reproduce

```sh
python -m vendor_assurance.remediation examples/remediation.json \
  --tenant synthetic-bank --as-of 2026-09-08T13:00:00Z \
  --decision examples/closure-reviewer.json --output output/closure
```

Omit `--decision` for pending human review. Outputs are `closure.json` (full original bundle, policy report and optional local decision) and `closure.html`. Existing output directories are refused. Treat exports as confidential when inputs are confidential.

## Evidence contract

One finding per bundle, bound to tenant and a full AWS resource identity: provider, account, region, environment, resource. The normalized check definition includes Prowler name/version, native check identifier and scanner configuration digest. Three check categories are accepted: public object storage, unrestricted administrative ingress and broad IAM permissions. These are categories, not implemented AWS probes. Specific native checks and their configuration require collector validation before live use. The fixture's native check ID and version are explicitly synthetic.

Baseline observation must explicitly fail. The change includes repository, revision, human approval and successful deployment reference for the same resource/revision. The latest unambiguous same-definition observation must explicitly pass after deployment and within the policy freshness window (default 24 hours, bounded 1–168). A newer failure/error/exclusion/not-observed result prevents closure. Missing findings are never treated as pass. Mismatched supplemental evidence conservatively blocks eligibility even when matching evidence exists.

Chronology uses timezone-aware timestamps. Evaluation time is operator supplied for reproducible replay, not a trusted server clock. Every decision recomputes and compares its report. Changed inputs or policy/date invalidate old reports. Human roles are local assertions, not authentication. A local reviewed-resolved record neither closes a ticket nor establishes that the source observation is authentic. Hashes bind serialized content; they are not signatures.

`eligible_for_human_closure` means only that these supplied records meet the policy. `unverified` requires investigation; it is not equivalent to a confirmed security failure. Risk acceptance is not implemented and must never be represented as remediation. Recurrence is detected when reassessing a supplied later observation; there is no continuous scheduler or automatic reopening of external tickets.

## Production gates

1. Consenting design partners and independently labeled representative closure cases.
2. Validate one real Prowler export mapping, exact check semantics, scanner version/configuration coverage and resource identities; preserve original artifacts and parser versions.
3. Read-only GitHub deployment evidence and approved read-only cloud collection, with authenticated tenant grants and revocation. A merged PR alone is insufficient.
4. Trusted collection time, provenance/signatures, immutable storage, retention controls and reproducible verification.
5. Authenticated separate change-approver and closure-reviewer permissions with audit history; evaluate separation-of-duties requirements per customer.
6. Fault injection covering partial scans, denied permissions, clock skew, replay, out-of-order evidence and compromised suppliers.

Do not add autonomous cloud changes, private Slack/Discord ingestion or customer outreach. Existing deployment and human review processes retain authority.
