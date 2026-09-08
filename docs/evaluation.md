# Evaluation and bounded evolution

Current evidence: deterministic regression tests and one deliberately authored synthetic bundle. There are no independent holdout results, measured buyer savings, production-accuracy claims or paid customers established by this repository. Passing tests does not prove zero risk.

## Proposed pilot scorecard

| Metric | Definition | Proposed gate / owner |
|---|---|---|
| Reviewer effort | Active review minutes including corrections per completed case | At least 30% reduction against paired customer baseline; pilot lead |
| Critical recall | Correct critical findings / independently labeled critical findings | Report numerator, denominator, confidence interval and every miss; risk lead decides threshold before pilot |
| Citation correctness | Findings whose source actually supports the conclusion / reviewed findings | At least 98%; any unsupported consequential conclusion blocks release; independent reviewers |
| False-alert burden | Dismissed findings / reviewed findings | No worse than agreed baseline; review lead |
| Access isolation | Unauthorized disclosures in adversarial tests | Zero observed; any failure blocks release; security lead |
| Decision completeness | Final decisions with required evidence, owner and approvals / final decisions | 100%; assurance lead |
| Commercial validation | Paying continuations / three design partners | At least two; product owner |

Log abstentions, excluded cases, unprocessable documents, p50/p95 latency, model cost and correction time alongside quality. Do not report quotation-match success as semantic correctness. Baseline review and product-assisted review should use comparable cases and account for reviewer learning. Track both elapsed renewal-cycle time and active effort; external supplier waiting time is not automatically product savings.

## Proposed release evaluation

At least 200 independently labeled cases including 50 critical cases, separated by vendor/document family from development data. These are minimum sample proposals, not proof of an acceptable critical-error rate. Two qualified reviewers adjudicate consequential disagreements. Include contradictory scopes, missing pages, unit differences, amendments, old evidence, wrong-tenant references, revoked access, changed documents during approval and malicious document instructions. Report results by failure class and customer segment; aggregate accuracy can hide critical failures.

## Proposed model loop (not implemented)

Retrieve within granted scope → propose structured claim with exact citation → verify source and scope → at most two repairs → human review or abstention. Freeze retrieval configuration, prompts, model versions, policy version and dataset IDs for each evaluation. No self-modification in production. Human release approval follows regression, independent holdout, cost and latency review. Canary a new version only after authorization; rollback on boundary failures or agreed quality regressions. Never train on customer evidence without separate permission.
