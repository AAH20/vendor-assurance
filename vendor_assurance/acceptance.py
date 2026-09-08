"""Permission-scoped synthetic acceptance runner; no remote targets or scripts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import uuid
from . import recovery

PACKAGE = 'synthetic-orders-v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def package_digest():
    # Bind the actual executable adapter, not only a friendly package name.
    return hashlib.sha256(Path(recovery.__file__).read_bytes()).hexdigest()


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timezone required')
    return result


def authorize(grant, tenant, now):
    if (grant.get('schema_version') != 1 or grant.get('mode') != 'synthetic'
            or grant.get('tenant') != tenant or not tenant
            or grant.get('package') != PACKAGE
            or grant.get('package_sha256') != package_digest()
            or grant.get('revoked') is not False
            or grant.get('purpose') != 'local_synthetic_acceptance'
            or not grant.get('authorization_reference')
            or not grant.get('requester') or not grant.get('approver')
            or grant['requester'] == grant['approver']):
        raise ValueError('grant scope or approval invalid')
    if not timestamp(grant['valid_from']) <= now < timestamp(grant['expires_at']):
        raise ValueError('grant expired or not yet valid')
    if (timestamp(grant['expires_at']) - timestamp(grant['valid_from'])).total_seconds() > 900:
        raise ValueError('grant lifetime exceeds 15 minutes')


def eligible(report):
    return (report.get('status') == 'exercise_passed_pending_human_review'
            and report.get('synthetic') is True
            and report.get('cleanup', {}).get('verified') is True
            and all(report.get('application_checks', {}).get(k) is True
                    for k in ('restored_records', 'committed_write')))


def execute(grant_path, tenant, output, scenario='healthy'):
    grant_path, output = Path(grant_path), Path(output)
    grant = json.loads(grant_path.read_text())
    started = time.monotonic()

    def check():
        current = json.loads(grant_path.read_text())
        if current != grant:
            raise ValueError('authorization changed during execution')
        authorize(current, tenant, datetime.now(timezone.utc))
        if time.monotonic() - started > 120:
            raise ValueError('cooperative execution budget exceeded')

    check()
    if scenario not in recovery.SCENARIOS:
        raise ValueError('unknown scenario')
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    run_id = str(uuid.uuid4())
    report = recovery.run(output / 'raw', scenario=scenario, control_check=check)
    errors = []
    try:
        check()
    except (ValueError, OSError, KeyError) as exc:
        errors.append(str(exc))
    receipt = dict(schema_version=1, run_id=run_id, tenant=tenant,
                   application='synthetic-orders-postgresql', package=PACKAGE,
                   package_sha256=grant['package_sha256'], grant_sha256=digest(grant),
                   runner_identity='local-process-unattested', synthetic=True,
                   completed_at=datetime.now(timezone.utc).isoformat(),
                   report=report, report_sha256=digest(report), errors=errors,
                   eligible_for_review=eligible(report) and not errors,
                   human_acceptance='pending')
    receipt['receipt_sha256'] = digest(receipt)
    with (output / 'receipt.json').open('x') as handle:
        import os
        os.chmod(handle.name, 0o600)
        json.dump(receipt, handle, indent=2, allow_nan=False)
        handle.write('\n')
    return receipt


def verify(receipt, tenant):
    """Integrity check only: hashes do not authenticate a producer."""
    payload = {k: v for k, v in receipt.items() if k != 'receipt_sha256'}
    return (receipt.get('tenant') == tenant and bool(tenant)
            and receipt.get('receipt_sha256') == digest(payload)
            and receipt.get('report_sha256') == digest(receipt.get('report'))
            and receipt.get('package_sha256') == package_digest()
            and receipt.get('human_acceptance') == 'pending'
            and receipt.get('eligible_for_review') is True
            and receipt.get('errors') == [] and eligible(receipt.get('report', {})))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grant', required=True, type=Path)
    parser.add_argument('--tenant', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--scenario', choices=recovery.SCENARIOS, default='healthy')
    args = parser.parse_args()
    receipt = execute(args.grant, args.tenant, args.output, args.scenario)
    print(json.dumps({'run_id': receipt['run_id'], 'eligible_for_review': receipt['eligible_for_review'], 'human_acceptance': 'pending'}))
    return 0 if receipt['eligible_for_review'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
