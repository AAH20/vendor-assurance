# A2Z Vendor Assurance

**Vendor risk assessment, evidence review, and human-reviewed renewal briefs.**

An Apache-2.0 offline reference for critical cloud, SaaS, and AI supplier reviews, maintained by [A2Z SOC](https://a2zsoc.com). It answers: *what conflicts, what is stale, what lacks evidence, and what must a reviewer acknowledge before recommending renewal?*

## Run the complete synthetic demonstration

Python 3.12+; no runtime dependencies, credentials, model calls, or network access required.

```sh
python -m unittest discover -s tests -v
python -m vendor_assurance examples/synthetic.json \
  --tenant synthetic-bank --as-of 2026-09-08 \
  --decision examples/human-decision.json --output output/demo
```

Open `output/demo/review.html`. The JSON companion exports the original bundle, findings, source hashes and character spans, and an advisory decision linked to the report hash. Output directories must be new. Omit `--decision` to leave review pending. The explicit date supports reproducible historical replay; operators must supply the current date for a current review.

The synthetic case produces five findings: a 4-hour versus 1-hour recovery objective conflict, expired backup evidence, a superseded audit claim, missing current backup evidence, and an overdue remediation. A synthetic human defers renewal. No supplier is contacted and no contract changes.

## Implemented

- Structured JSON import for one tenant/vendor/service per bundle.
- Exact source quotation and span validation; versioned document families and content hashes.
- Deterministic conflict, expiry, supersession, missing-evidence and overdue-action checks.
- Tenant equality checks before review and decisions.
- Human-role-only advisory decisions with explicit acknowledgement of all findings.
- Recomputed report comparison rejects changed evidence, modified reports and stale evaluation dates.
- Portable JSON evidence package and escaped, static HTML brief.
- Regression tests and GitHub Actions on Python 3.12–3.14.

## Deliberate limits

This is a trusted-local-operator prototype, **not an authenticated multi-tenant service**. A caller can supply their own tenant and role; those fields are not identity proof. File permissions protect local bundles. Hashes are integrity references, not signatures or immutable audit storage. Source matching verifies quotation fidelity, not entailment, authenticity, security posture or legal compliance. Claims, obligation keys, owners, evidence validity dates and scope are operator supplied. Different values trigger review rather than determining breach of contract. No findings does not mean approval.

No PDF/OCR extraction, model-generated assessments, live monitoring, remediation scheduling, SSO, production authorization, Slack/Discord connection, payment or contract execution is implemented. LangGraph, GraphRAG, Pinecone and due-diligence agent adapters are future integrations gated by evaluation. No CNCF endorsement or deployment is implied. DMs, private-channel ingestion and automated outreach are excluded.

## Remediation assurance extension

Verify closure eligibility from normalized AWS/Prowler-style evidence, approved revision and deployment references, and a fresh explicit passing observation. This is an offline synthetic workflow, not a native Prowler or GitHub collector.

```sh
python -m vendor_assurance.remediation examples/remediation.json \
  --tenant synthetic-bank --as-of 2026-09-08T13:00:00Z \
  --decision examples/closure-reviewer.json --output output/closure
```

The assurance and remediation suites contain 46 regression tests. See the [evidence contract and limits](docs/remediation.md) and [design-partner pilot package](docs/design-partner-pilot.md). No design partners have been recruited by this repository.

## Executable recovery exercise

A real PostgreSQL backup is restored into a disposable second cluster and verified through a local HTTP application. Synthetic records only; existing databases are never targeted. See [setup, measurement boundaries, failure scenarios and cleanup](docs/recovery.md).

```sh
python -m vendor_assurance.recovery --output output/recovery
A2Z_RECOVERY_INTEGRATION=1 python -m unittest discover -s tests -v
```

Requires PostgreSQL server/client tools. Integration tests are explicitly opt-in locally and run in a separate GitHub CI job.

## Authenticated managed pilot foundation

A loopback control service authenticates separate requester, approver, runner and reviewer credentials, enforces scoped job transitions, and binds review to exact execution evidence. The full demo runs a real synthetic recovery; its reviewer is simulated.

```sh
python -m vendor_assurance.managed_demo --output output/managed-demo
```

See [setup, authorization and operating limits](docs/managed-pilot.md) and the [paid-pilot worksheet](docs/paid-pilot-worksheet.md). This is not a production service or a paid customer deployment.

## Integration and benchmark kit

Run the local PostgreSQL adapter against a versioned acceptance manifest and produce a fair comparison package:

```sh
python -m vendor_assurance.integration --manifest examples/acceptance-manifest.json --output output/integration
```

The demonstration has no baseline and makes no savings claim. [The comparison protocol](docs/integration-benchmark.md) documents pairing, exclusions, evidence validation and the external-adapter decision gate. The local execution benchmark has no external-vendor baseline; the separate AWS read-only adapter below does not execute restores.

## Read-only AWS Backup evidence adapter

The official Boto3 adapter reads one authorized RDS restore job and checks its evidence against an application receipt. SDK Stubber tests run without AWS credentials or account access. Live collection has not been validated.

```sh
python -m vendor_assurance.aws_backup review --grant examples/aws-backup/grant.json --capture examples/aws-backup/capture.json --application examples/aws-backup/application.json --tenant synthetic-bank --as-of 2026-09-08T12:00:00Z --output aws-review.json
```

See [authorization, setup, evidence interpretation and limits](docs/aws-backup-adapter.md). Restore execution remains absent from this adapter.

## Application recovery acceptance runner

Run the synthetic PostgreSQL exercise with expiring authorization, code-bound test scope, and an integrity-linked evidence receipt. Human acceptance stays pending. See [setup, evaluation and trust limitations](docs/acceptance-runner.md). Customer RDS execution and authenticated approval are not implemented by this runner.

## Recovery acceptance gateway foundation

The managed service now binds approvals to adapter code and submissions to a single authenticated execution. Concurrent claim replay and credential substitution are rejected; review covers both scope and evidence. See [protocol changes, demonstration and remaining production gaps](docs/recovery-acceptance-gateway.md).

## Design and validation

- [Application recovery assurance pilot: scope, qualification and KPIs](docs/recovery-assurance-pilot.md)
- [Architecture and production gates](docs/architecture.md)
- [Evaluation, KPIs and bounded evolution](docs/evaluation.md)
- [Market hypothesis, alternatives and paid validation](docs/market.md)
- [Public/private publication boundary](docs/publication.md)
- [Security](SECURITY.md)

Related projects: [permissioned contributor agent](https://github.com/AAH20/permissioned-contributor-agent), [trusted community marketplace](https://github.com/AAH20/trusted-community-marketplace), and [A2Z due-diligence agents](https://github.com/AAH20/A2Z_due-diligence-agents). These are linked projects, not dependencies or executed integrations in this release.
