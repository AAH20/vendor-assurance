# Recovery integration and benchmark kit

This release integrates the executable local PostgreSQL runner with a versioned acceptance manifest and paired comparison evaluator. It does not integrate AWS Backup, Veeam, Rubrik or Velero, benchmark those products, or establish paid demand. The first external adapter must be chosen from a consenting design partner's actual stack.

## Run

```sh
python -m vendor_assurance.integration --manifest examples/acceptance-manifest.json --output output/integration
```

PostgreSQL server/client prerequisites and isolation limits from [recovery.md](recovery.md) apply. This executes a real synthetic backup/restore and application transaction. Outputs include the manifest, raw recovery evidence, normalized runs and an HTML/JSON comparison. No baseline is invented: paired cases are zero and active-effort savings are null.

Re-evaluate an existing run set without executing anything:

```sh
python -m vendor_assurance.benchmark --manifest examples/acceptance-manifest.json --runs output/integration/runs.json --output output/comparison
```

## Acceptance manifest v1

The manifest binds a tenant, application, exact workload description digest, required checks, dependencies, recovery-time limit, data-age limit, cleanup requirement and timing boundary. The built-in adapter validates the supported workload digest before running. Its only application is `synthetic-orders-postgresql`; its dependencies are PostgreSQL and the local HTTP API. This is an executable acceptance contract, not arbitrary natural-language instructions for an agent.

The timing boundary is source stopped through successful application write/read validation. Backup creation, disaster detection, human mobilization and cleanup are outside this duration. Changing any manifest field invalidates the manifest hash of previous run envelopes. Re-evaluate with an explicitly chosen new manifest and a new evidence record; do not silently relabel old runs.

## Normalized evidence envelope v1

Each run contains `run_id`, `case_id`, `workflow` (`baseline` or `candidate`), server-independent tenant assertion, adapter identifier, manifest/workload hashes, timing boundary, original report, report hash and nullable `active_minutes`. The envelope takes a snapshot of the original report. This offline format records provenance but does not authenticate it. Use the managed pilot for credential-based job control; this evaluator alone is not an access-control service.

The current evaluator only accepts synthetic reports. A real customer adapter needs a reviewed schema for source identities, original tool artifacts, collection/validation times, explicit checks, tool and parser versions, cleanup evidence, retention and grants. Never convert a missing check into a passing result. Never declare a third-party tool integrated merely because its name appears in an envelope.

## Fair comparison protocol

1. Pre-agree the acceptance manifest, test scenarios, environment characteristics and workload with the customer. Record dependency versions and execution order in the exercise record.
2. Run the existing workflow and candidate independently against comparable cases. Alternate or randomize order where feasible to reduce learning/cache effects. Account for setup and maintenance separately.
3. Assign one baseline and one candidate run to each case. Duplicate run IDs or duplicate case/workflow combinations are rejected. Manifest, tenant, workload, timing and scenario mismatches are rejected.
4. Collect active effort independently, including setup required for that exercise, corrections and review. Do not substitute elapsed restore time. Unknown effort remains null, not zero.
5. Evaluate both with the same acceptance rules. Report quality disagreements for adjudication. Only pairs in which both workflows are eligible and both effort measurements exist contribute to effort-reduction arithmetic.
6. Reduction fraction = (sum baseline active minutes − sum candidate active minutes) / sum baseline active minutes. A zero denominator produces null. Missing/unmatched pairs remain visible; inspect exclusions before interpreting the aggregate.
7. Keep independent correctness assessment separate. The kit has no ground-truth adjudication dataset and reports independent accuracy as unmeasured. No confidence interval or population-level inference is produced from this demonstration.

Matching metadata does not prove that two runs had equivalent conditions, truthful labor measurements or independent execution. These remain reviewer responsibilities. A claimed faster result with failed acceptance cannot contribute to a speedup claim.

## Adapter decision worksheet

| Candidate | Existing capability to evaluate first | Needed before adapter work |
|---|---|---|
| AWS Backup | Restore testing and optional validation | Authorized sandbox, selected resource type, original test/validation artifacts |
| Veeam | SureBackup recovery verification | Customer version, license/access, test scripts and original result export |
| Rubrik | Recovery simulation, validation and reporting | Authorized test environment and agreed result interface |
| Velero | Kubernetes backup/restore and hooks | Isolated cluster, storage plugin, app acceptance hooks and artifacts |
| Existing scripts/CI | Customer-defined recovery workflow | Versioned scripts, actual execution evidence and maintenance baseline |

Official references: [AWS](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html), [Veeam](https://helpcenter.veeam.com/docs/vbr/userguide/surebackup_hiw.html), [Rubrik](https://www.rubrik.com/products/cyber-recovery-simulation), [Velero](https://github.com/velero-io/velero). These describe alternatives, not comparative results measured by this repository.

## Next customer gate

Complete the [paid-pilot worksheet](paid-pilot-worksheet.md). Obtain a named owner, chosen stack, agreed fee/scope, written access authorization and permitted evidence before external execution. Real customer acceptance, customer-side integration and willingness to pay remain outstanding. No outreach or deployment is performed by this kit.
