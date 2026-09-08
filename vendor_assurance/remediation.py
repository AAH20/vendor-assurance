"""Offline closure eligibility for operator-supplied AWS evidence exports.

No collection, authentication, deployment or external ticket closure is performed.
"""
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
from .core import digest, required_text

POLICY = 'a2z-remediation/1'
CHECKS = {
    'object_storage_public_access': 'Observed public-access exposure under the configured scanner check only.',
    'administrative_ingress': 'Observed unrestricted administrative ingress under the configured scanner check only.',
    'iam_broad_permission': 'Observed broad permission under the configured scanner check only.',
}


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timezone-aware timestamp required')
    return parsed.astimezone(timezone.utc)


def assess(bundle, tenant, as_of, max_age_hours=24):
    if tenant != bundle['tenant']:
        raise PermissionError('tenant scope denied')
    if type(max_age_hours) is not int or not 1 <= max_age_hours <= 168:
        raise ValueError('freshness window must be 1–168 hours')
    now = instant(as_of)
    finding = bundle['finding']
    identity = finding['identity']
    if set(identity) != {'provider', 'account', 'region', 'environment', 'resource'}:
        raise ValueError('complete resource identity required')
    if identity['provider'] != 'aws':
        raise ValueError('reference supports AWS exports only')
    for value in identity.values():
        required_text(value)
    required_text(finding['id'])
    required_text(finding['owner'])
    if finding['check'] not in CHECKS:
        raise ValueError('unsupported check')
    definition = finding['definition']
    if set(definition) != {'scanner', 'version', 'check_id', 'configuration_sha256'}:
        raise ValueError('complete scanner definition required')
    for value in definition.values():
        required_text(value)
    if definition['scanner'] != 'prowler':
        raise ValueError('reference supports normalized Prowler exports only')
    reasons = []
    def reject(reason):
        if reason not in reasons:
            reasons.append(reason)
    observations = bundle['observations']
    ids = set()
    for observation in observations:
        if observation['id'] in ids:
            raise ValueError('duplicate observation id')
        ids.add(required_text(observation['id']))
        required_text(observation['source'])
        if observation['status'] not in ('pass', 'fail', 'error', 'excluded', 'not_observed'):
            raise ValueError('unknown observation status')
        instant(observation['collected_at'])
    baseline = [o for o in observations if o['id'] == finding['baseline_observation']]
    if len(baseline) != 1:
        reject('missing_baseline')
    elif baseline[0]['status'] != 'fail' or baseline[0]['identity'] != identity or baseline[0]['definition'] != definition:
        reject('invalid_baseline')
    change = bundle['change']
    approval = change['approval']
    deployment = change['deployment']
    for key in ('repository', 'revision', 'id'):
        required_text(change[key])
    required_text(approval['actor'])
    approved_at = instant(approval['at'])
    deployed_at = instant(deployment['at'])
    if approval['role'] != 'human_change_approver' or approval['decision'] != 'approve':
        reject('change_not_human_approved')
    if approval['revision'] != change['revision']:
        reject('approval_revision_mismatch')
    if deployment['revision'] != change['revision'] or deployment['repository'] != change['repository']:
        reject('deployment_revision_mismatch')
    if deployment['identity'] != identity:
        reject('deployment_identity_mismatch')
    if deployment['status'] != 'success':
        reject('deployment_not_successful')
    required_text(deployment['run_reference'])
    if approved_at > deployed_at or deployed_at > now:
        reject('invalid_change_chronology')
    if baseline and instant(baseline[0]['collected_at']) > approved_at:
        reject('baseline_after_approval')
    after = [o for o in observations if o['id'] != finding['baseline_observation']]
    matching = []
    for o in after:
        if o['identity'] != identity:
            reject('observation_identity_mismatch')
        elif o['definition'] != definition:
            reject('check_definition_mismatch')
        else:
            matching.append(o)
    latest = None
    if not matching:
        reject('missing_verification')
    else:
        newest = max(instant(o['collected_at']) for o in matching)
        candidates = [o for o in matching if instant(o['collected_at']) == newest]
        if len(candidates) != 1:
            reject('ambiguous_latest_observation')
        else:
            latest = candidates[0]
            if newest <= deployed_at:
                reject('verification_not_after_deployment')
            if newest > now:
                reject('future_observation')
            if (now - newest).total_seconds() > max_age_hours * 3600:
                reject('stale_verification')
            if latest['status'] != 'pass':
                reject('verification_' + latest['status'])
    return dict(policy=POLICY, tenant=tenant, finding=finding['id'], as_of=as_of,
                max_age_hours=max_age_hours, bundle_sha256=digest(bundle),
                status='eligible_for_human_closure' if not reasons else 'unverified',
                reasons=reasons, latest_observation=latest['id'] if latest else None,
                scope=CHECKS[finding['check']], external_action=False)


def close(bundle, report, tenant, as_of, actor, role, rationale):
    if role != 'human_closure_reviewer':
        raise PermissionError('human closure reviewer required')
    required_text(actor)
    required_text(rationale)
    if report != assess(bundle, tenant, as_of, report['max_age_hours']):
        raise ValueError('stale or modified report')
    if report['status'] != 'eligible_for_human_closure':
        raise ValueError('unverified evidence cannot close a finding')
    return dict(actor=actor, role=role, rationale=rationale, tenant=tenant, as_of=as_of,
                status='locally_reviewed_resolved', report_sha256=digest(report), external_action=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--tenant', required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--decision', type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text())
    report = assess(bundle, args.tenant, args.as_of)
    decision = close(bundle, report, args.tenant, args.as_of, **json.loads(args.decision.read_text())) if args.decision else None
    args.output.mkdir(parents=True, exist_ok=False)
    package = dict(bundle=bundle, report=report, decision=decision)
    (args.output/'closure.json').write_text(json.dumps(package, indent=2)+'\n')
    content = html.escape(json.dumps(dict(report=report, decision=decision), indent=2))
    (args.output/'closure.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>A2Z Remediation Assurance</title><style>body{font:18px system-ui;max-width:1000px;margin:40px auto;padding:24px;background:#101b2a;color:#edf3fc}pre{white-space:pre-wrap;background:#1d3047;padding:24px}a{color:#85caff}</style><h1>Remediation assurance</h1><p>Offline evidence review. Source authenticity is operator asserted; no external closure or deployment.</p><pre>'+content+'</pre><p><a href="https://a2zsoc.com">A2Z SOC</a></p></html>')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
