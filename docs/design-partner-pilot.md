# Design-partner pilot package — draft, not an outreach campaign

Target: a regulated customer and its managed-cloud provider with recurring remediation verification work. Seek three consenting partners; none are claimed recruited. No messages have been sent. Obtain explicit authorization before outreach and separate written data-access permission before collecting evidence.

## Qualification interview

- Who owns closure verification, and who can approve a paid pilot?
- How many findings were closed in the last month, and how many required supplier evidence reconciliation?
- Which existing scanner, ticket and deployment tools are already licensed?
- Show an authorized example of a closure that was disputed, reopened or expensive to verify.
- Can configuration of those existing tools solve the problem adequately?
- What representative evidence can be shared, with which retention and deletion terms?

## Fixed-scope experiment

One AWS environment, one Prowler version/configuration, GitHub deployment exports and three agreed check definitions. Begin with offline exports. No production writes. Customer supplies a representative sample including correctly closed, unresolved, stale, mismatched, excluded, failed-scan and recurring cases. Do not choose only cases that favor the product.

Record current reviewer effort and results before introducing assistance. Independently label cases, compare the same acceptance policy, adjudicate disagreements and record selection bias. Agree data owners, named reviewers, access scope, stop conditions, deletion deadline and a fixed pilot fee before real evidence intake. Pricing is not yet validated; no invented market-average or ROI claim.

## Scorecard and stop rules

| Metric | Denominator / measurement | Proposed gate |
|---|---|---|
| False closure | Unresolved/unverified cases marked resolved divided by labeled unresolved/unverified cases | Zero observed; any case blocks release |
| Evidence completeness | Accepted closure packages with every required field divided by accepted packages | 100% |
| Reviewer effort | Active minutes including collection, corrections and review per comparable case | At least 30% below baseline |
| Reproducibility | Identical policy decisions from preserved inputs divided by replayed cases | 100% |
| Unknown handling | Missing/stale/mismatched/failed evidence left unverified divided by labeled boundary cases | 100% |
| Commercial validation | Partners paying to continue divided by three pilot partners | At least two |

Report counts and confidence intervals, not percentages alone. Synthetic regression results do not satisfy independent accuracy gates. Zero observed false closures does not prove zero error probability. Track integration hours and false blocks as well as saved review time. Stop or integrate into incumbents if configuring their tools gives equivalent results at lower total cost.

## Commercial boundary

Remediation requests may later become marketplace engagements with explicit deliverables and verified acceptance. Paid placement and provider relationships must not influence verification. No customer evidence, identities, contract terms or negotiated prices belong in the public repository.
