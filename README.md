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

## Design and validation

- [Architecture and production gates](docs/architecture.md)
- [Evaluation, KPIs and bounded evolution](docs/evaluation.md)
- [Market hypothesis, alternatives and paid validation](docs/market.md)
- [Public/private publication boundary](docs/publication.md)
- [Security](SECURITY.md)

Related projects: [permissioned contributor agent](https://github.com/AAH20/permissioned-contributor-agent), [trusted community marketplace](https://github.com/AAH20/trusted-community-marketplace), and [A2Z due-diligence agents](https://github.com/AAH20/A2Z_due-diligence-agents). These are linked projects, not dependencies or executed integrations in this release.
