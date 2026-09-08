# Recovery assurance paid-pilot worksheet

Unexecuted planning worksheet. No customer commitment, pricing agreement, access authorization or legal acceptance is implied. Do not place completed customer information in this public repository.

## Required customer input

| Field | To agree privately |
|---|---|
| Customer / provider | Legal entities and named service owner |
| Budget owner | Person authorized to approve a pilot fee |
| Application and stack | One application, backup tool/version, deployment and dependencies |
| Environment | Explicit nonproduction account, resources and isolation boundary |
| Written authorization | Approver, scope, allowed actions, validity period, withdrawal route |
| Data | Permitted synthetic/sanitized data, storage, access and deletion deadline |
| Objective | Recovery-time limit, data-age limit and exact timing boundaries |
| Acceptance transaction | What must work, required dependencies and evidence |
| Constraints | Execution window, spending cap, resource cap and stop conditions |
| Review | Separate approver and acceptance reviewer, escalation owner |
| Commercial scope | Fixed fee, included exercises, integration scope, support coverage and exclusions |

## Proposed delivery sequence

1. Qualify pain using the existing recovery process and recent authorized examples. Check whether configuring existing tools is sufficient.
2. Agree the fee, scope, evidence handling and written access authorization. No assumed price or vendor-specific access.
3. Establish a baseline for active engineering/review time, infrastructure expense and evidence completeness.
4. Configure one adapter and run a synthetic dry run in an authorized nonproduction environment.
5. Run the agreed exercise and deliberate failure cases. Do not use a successful infrastructure restore as a substitute for application acceptance.
6. Deliver evidence, cleanup verification, limitations and proposed corrective actions for human review.
7. Compare actual costs and outcomes with the baseline. Continue only when the customer chooses a paid next step.

## Acceptance and economics

Use the KPI definitions in the recovery and design-partner documents. Require zero observed incorrect success reports and complete evidence/cleanup for accepted exercises. Target at least 30% lower active effort, while reporting sample size and selection limitations. Track integration hours, support hours and infrastructure cost separately.

Pilot contribution = agreed fee − delivery labor − infrastructure − third-party costs. Ongoing pricing must cover adapter maintenance and support, not merely execution cost. Neither pricing nor willingness to pay has been validated. Any contractual service levels and liability terms require agreement through the parties' own procurement/legal process.

## Stop conditions

Authorization withdrawn; unexpected production access; data outside the agreed scope; spending/resource limit exceeded; cleanup failure; unsupported success conclusion; or insufficient evidence to decide. Stop testing, retain only authorized evidence and follow the agreed escalation process. No automatic production restoration or external communications.

## Current status

Customer: not selected. Fee: not agreed. Stack: not selected. Written authorization: not supplied. Real customer acceptance: not obtained. The repository demonstration is synthetic and its reviewer action is explicitly simulated.
