# Application recovery assurance pilot

A proposed, independently operated [A2Z SOC](https://a2zsoc.com) pilot for teams that need reviewable evidence that a restored application works. This repository is an experimental OSS foundation, not a production managed service. No paid customer or live AWS validation is claimed, and no CNCF endorsement or deployment is implied.

## The question we will test

Can a scoped evidence and review workflow reduce the active work needed to prepare and accept a recovery exercise, while preserving the customer's application checks and approval requirements? This is a commercial hypothesis, not a demonstrated savings claim.

The intended participant is an MSP or application owner with recurring recovery exercises, an accountable reviewer, and an existing restore process. The pilot complements that process: customer operators execute restores using their existing tooling.

## Proposed scope

- One nonproduction application, one AWS account and region, and one supported RDS PostgreSQL instance pattern, initially using synthetic data.
- One agreed baseline/candidate exercise pair, with the same workload, required application checks, dependencies, and measurement boundaries.
- Read-only collection of explicitly authorized AWS restore-job metadata, plus a customer-supplied application validation receipt.
- Two evidence replays, two review sessions, and a documented handover. Replays are offline evaluations, not additional live restores.

The final scope and schedule depend on feasibility review. Production recovery, Aurora/composite restore patterns, automatic remediation, outreach, private-channel ingestion, and contract execution are outside this pilot.

## Deliverables

1. A versioned acceptance manifest and authorization record identifying scope, actors, required evidence, expiration, retention, and cleanup responsibilities.
2. A private evidence report identifying missing, stale, contradictory, or out-of-scope observations, with references to the exact evidence reviewed.
3. A baseline/candidate comparison with explicit exclusions, measured operator effort, application validation outcomes, and reviewer acceptance or rejection.
4. A limitations register and handover documenting repeatability, unresolved risks, and the decision to stop, revise, or proceed.

Customer evidence remains private. Any public case study, metrics, or quotations require separate written permission.

## Qualification and authorization

Before execution, identify the application owner, budget owner, customer operator, and independent reviewer. Confirm the supported stack, a recent example of the current exercise, its frequency, and measured effort. Agree the test recipe, commercial terms, account permissions, data handling, resource cleanup, and cloud-spend ceiling in writing.

Live access requires explicit written authorization from the relevant account administrator and scoped credentials. A local grant file alone does not establish that authorization. The adapter cannot start restores or delete resources. Customer operators retain responsibility for those actions and provide application validation evidence. No customer access or spend is authorized by this document.

## KPIs and acceptance

Targets must be agreed before the exercise; the pilot does not promise zero error or regulatory compliance.

| Measure | Definition and decision rule |
| --- | --- |
| Evidence completeness | Required evidence items present and valid / required items. Every mandatory item must pass before acceptance. |
| Application correctness | All agreed read, write, and dependency checks pass; a completed infrastructure restore alone is insufficient. |
| Recovery timing | Measure the agreed start/end events against the customer's target. AWS job timing and local demo timing have different boundaries and cannot be compared directly. |
| Data recovery age | Compare the latest recovered application transaction with the agreed reference time; do not substitute backup creation time. |
| Active operator effort | Record hands-on minutes separately from elapsed duration. Report savings only for eligible paired runs with both effort measurements. |
| Reviewer disagreement | Record every case where the workflow's eligibility assessment differs from the reviewer's decision, with a reason and severity. |
| Scope and approval violations | Target zero; any violation stops the pilot pending investigation and renewed authorization. |
| Cleanup completion | Customer confirms agreed resources and application probes are cleaned up, with supporting evidence. |

One pair establishes feasibility, not statistically proven accuracy, market demand, or generalizable savings. Missing evidence produces an unverified result rather than an inferred pass.

## Evaluation and evolution loop

Freeze the acceptance manifest and evaluator version before each exercise. Collect scoped evidence, evaluate it, obtain human review, and record disagreements. Convert confirmed failures into regression fixtures; propose changes with versioned rationale and replay the fixed suite before another exercise. A human approves every scope or evaluator change. Regressions in authorization, isolation, or mandatory checks block promotion. No autonomous policy changes or self-deployment are enabled.

## Current implementation and tradeoffs

The repository includes real local synthetic PostgreSQL recovery exercises, a loopback control-service demonstration with separate role credentials, offline comparison tools, and a read-only AWS Backup SDK adapter tested using stubbed responses. The demonstration's reviewer is simulated. Live AWS collection and customer outcomes remain unvalidated.

The AWS review depends on operator-supplied application receipts; it does not independently attest their truth. Production SSO, durable distributed execution, hard resource quotas, and production authorization infrastructure are absent. GraphRAG, LangGraph, and Pinecone integrations are not implemented; they are unnecessary to establish the first deterministic acceptance baseline.

See the [AWS adapter limits](aws-backup-adapter.md), [comparison protocol](integration-benchmark.md), [managed-pilot limitations](managed-pilot.md), and [evaluation parameters](evaluation.md).

## Commercial discussion

Deployment assistance, managed operation, and ongoing support can be scoped separately after technical qualification. Pricing, service commitments, and customer-specific obligations are agreed privately; no public price or SLA is offered here. Regulated workloads require additional customer-specific security, legal, residency, and operational review before any expansion beyond synthetic nonproduction use.

Use the [pilot worksheet](paid-pilot-worksheet.md) to prepare that discussion and visit [a2zsoc.com](https://a2zsoc.com) for the project owner's site. No outreach or customer deployment is initiated by publication of this proposal.
