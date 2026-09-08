"""Manifest-bound recovery evidence evaluation and paired workflow comparison.

Inputs are local operator-supplied records. Provenance is recorded, not independently attested.
"""
import argparse
import copy
import html
import json
import math
from pathlib import Path
from .core import digest, required_text

TIMING = 'source_stopped_to_application_transaction_verified'
CHECKS = ['restored_records', 'committed_write']
WORKLOAD = 'synthetic-orders-v1: three orders with ids 1,2,3 and amounts 10,20,30; write probe inserts id 4 amount 40'


def validate_manifest(manifest):
    if manifest['schema_version'] != 1:
        raise ValueError('unsupported manifest version')
    for key in ('id', 'tenant', 'application', 'workload_sha256'):
        required_text(manifest[key])
    if len(manifest['workload_sha256']) != 64 or any(c not in '0123456789abcdef' for c in manifest['workload_sha256']):
        raise ValueError('workload SHA-256 required')
    if manifest['timing_boundary'] != TIMING:
        raise ValueError('unsupported timing boundary')
    if manifest['required_checks'] != CHECKS or manifest['dependencies'] != ['postgresql', 'http_api']:
        raise ValueError('only the current PostgreSQL/HTTP acceptance contract is supported')
    if manifest['cleanup_required'] is not True:
        raise ValueError('cleanup required')
    for key in ('rto_seconds', 'rpo_seconds'):
        number(manifest[key])
        if manifest[key] <= 0: raise ValueError('positive objective required')
    return manifest


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('finite nonnegative number required')
    return value


def envelope(report, manifest, case_id, workflow, run_id, active_minutes=None):
    validate_manifest(manifest)
    report = copy.deepcopy(report)
    if report.get('synthetic') is not True:
        raise ValueError('current adapter permits synthetic reports only')
    return dict(schema_version=1, run_id=run_id, case_id=case_id, tenant=manifest['tenant'],
                workflow=workflow, manifest_sha256=digest(manifest), workload_sha256=manifest['workload_sha256'],
                adapter='a2z-local-postgres-report/1', timing_boundary=TIMING,
                active_minutes=active_minutes, report_sha256=digest(report), report=report)


def evaluate(run, manifest):
    validate_manifest(manifest)
    if run['tenant'] != manifest['tenant']: raise PermissionError('tenant mismatch')
    for key in ('run_id', 'case_id', 'adapter'):
        required_text(run[key])
    if run['schema_version'] != 1 or run['workflow'] not in ('baseline', 'candidate'):
        raise ValueError('invalid run schema or workflow')
    if run['manifest_sha256'] != digest(manifest) or run['workload_sha256'] != manifest['workload_sha256']:
        raise ValueError('manifest or workload mismatch')
    if run['timing_boundary'] != manifest['timing_boundary']:
        raise ValueError('incomparable timing boundary')
    if run['active_minutes'] is not None: number(run['active_minutes'])
    report = run['report']
    if run['report_sha256'] != digest(report): raise ValueError('modified report')
    if report.get('synthetic') is not True: raise ValueError('current evaluator permits synthetic evidence only')
    required_text(report.get('scenario'))
    reasons = []
    for check in manifest['required_checks']:
        if report.get('application_checks', {}).get(check) is not True:
            reasons.append('missing_or_failed_check:' + check)
    if report.get('cleanup', {}).get('verified') is not True:
        reasons.append('cleanup_unverified')
    for field, objective in (('recovery_seconds', 'rto_seconds'), ('measured_data_age_seconds', 'rpo_seconds')):
        value = report.get(field)
        if value is None:
            reasons.append('missing_metric:' + field)
        elif number(value) > manifest[objective]:
            reasons.append('objective_exceeded:' + field)
    if report.get('status') != 'exercise_passed_pending_human_review':
        reasons.append('exercise_not_passed')
    return dict(run_id=run['run_id'], case_id=run['case_id'], workflow=run['workflow'],
                scenario=report['scenario'], eligible=not reasons, reasons=reasons,
                active_minutes=run['active_minutes'], human_acceptance='not_established')


def compare(manifest, runs):
    validate_manifest(manifest)
    evaluated=[]
    seen_ids=set()
    seen_cases=set()
    for run in runs:
        result=evaluate(run,manifest)
        key=(run['case_id'],run['workflow'])
        if run['run_id'] in seen_ids or key in seen_cases:
            raise ValueError('duplicate run or case/workflow pair')
        seen_ids.add(run['run_id'])
        seen_cases.add(key)
        evaluated.append(result)
    pairs=[]
    unmatched=[]
    for case in sorted({r['case_id'] for r in evaluated}):
        group={r['workflow']:r for r in evaluated if r['case_id']==case}
        if set(group)!= {'baseline','candidate'}:
            unmatched.append(case)
            continue
        baseline,candidate=group['baseline'],group['candidate']
        if baseline['scenario']!=candidate['scenario']: raise ValueError('paired scenarios differ')
        pairs.append(dict(case_id=case, baseline=baseline, candidate=candidate))
    measured=[p for p in pairs if all(p[w]['eligible'] and p[w]['active_minutes'] is not None for w in ('baseline','candidate'))]
    base=sum(p['baseline']['active_minutes'] for p in measured)
    cand=sum(p['candidate']['active_minutes'] for p in measured)
    savings=(base-cand)/base if measured and base>0 else None
    return dict(schema_version=1, manifest_sha256=digest(manifest), runs=evaluated, pairs=pairs,
                paired_cases=len(pairs), unmatched_cases=unmatched, effort_measured_pairs=len(measured),
                baseline_active_minutes=base if measured else None, candidate_active_minutes=cand if measured else None,
                active_effort_reduction_fraction=savings,
                quality_disagreements=[p['case_id'] for p in pairs if p['baseline']['eligible']!=p['candidate']['eligible']],
                commercial_validation='not_established', independent_accuracy='not_measured',
                limitations=['Synthetic/operator-supplied records only; metadata equality does not prove comparable execution conditions.',
                             'Elapsed recovery duration is not active labor. Missing labor measurements remain null.',
                             'No ground-truth labels, confidence intervals, customer acceptance or paid demand established.'])


def write_comparison(output, result):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    (output/'benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
    rows=''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in ('case_id','workflow','eligible','active_minutes'))+'</tr>' for r in result['runs'])
    (output/'benchmark.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Recovery benchmark</title><style>body{font:18px system-ui;max-width:1000px;margin:40px auto;padding:24px;background:#101b2a;color:#edf3fc}td,th{padding:14px;text-align:left;border-bottom:1px solid #738599}a{color:#85caff}</style><h1>Recovery integration benchmark</h1><p>Paired cases: '+str(result['paired_cases'])+'</p><p>Measured active-effort reduction: '+html.escape(str(result['active_effort_reduction_fraction']))+' (null means unmeasured)</p><table><tr><th>Case</th><th>Workflow</th><th>Eligible</th><th>Active minutes</th></tr>'+rows+'</table><p>Synthetic evidence. No customer acceptance or independent accuracy established.</p><p><a href="https://a2zsoc.com">A2Z SOC</a></p></html>')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True,type=Path)
    parser.add_argument('--runs',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    result=compare(json.loads(args.manifest.read_text()),json.loads(args.runs.read_text()))
    write_comparison(args.output,result)
    print(json.dumps({'paired_cases':result['paired_cases'],'effort_reduction':result['active_effort_reduction_fraction']}))


if __name__=='__main__': main()
